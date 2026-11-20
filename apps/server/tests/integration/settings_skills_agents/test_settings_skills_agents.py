"""Integration tests for SET-001, SET-002, SKL-001, SKL-002, and AGN-003."""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from agent_cf_server.bootstrap.config import ServerSettings
from agent_cf_server.bootstrap.server import create_app
from agent_cf_server.infrastructure.agents.repository import AgentRepository
from agent_cf_server.infrastructure.persistence.database import Database
from agent_cf_server.infrastructure.settings.inventory import load_runtime_inventory
from agent_cf_server.infrastructure.settings.repository import (
    InUseError,
    ResourceConflictError,
    ResourceNotFoundError,
    SettingsRepository,
)
from agent_cf_server.infrastructure.skills.repository import (
    SkillRepository,
    compute_skill_bundle_hash,
    sync_skills_from_directory,
)


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "test_catalogs.sqlite3"
    database = Database(db_path)
    database.migrate()
    return database


@pytest.fixture
def client(tmp_path):
    settings = ServerSettings(
        database_path=tmp_path / "api_test.sqlite3",
        temporal_enabled=False,
    )
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


# =============================================================================
# SET-001: Runtime & Model Inventory
# =============================================================================

def test_set001_runtime_inventory_loads_reference():
    inventory = load_runtime_inventory()
    assert inventory.schema_version == 1
    assert "codex" in inventory.runtimes
    assert "antigravity" in inventory.runtimes

    codex = inventory.runtimes["codex"]
    assert codex.adapter_id == "codex"
    assert codex.observed_cli_version == "0.147.0"
    model_ids = [m.runtime_model_id for m in codex.models]
    assert "gpt-5.6-sol" in model_ids
    # Unknown IDs are kept as None, not guessed
    ag = inventory.runtimes["antigravity"]
    assert any(m.runtime_model_id is None for m in ag.models)


def test_set001_runtime_inventory_endpoint(client):
    res = client.get("/v1/settings/runtime-inventory")
    assert res.status_code == 200
    data = res.json()
    assert "runtimes" in data
    assert "codex" in data["runtimes"]
    assert "antigravity" in data["runtimes"]


# =============================================================================
# SET-002: Settings Persistence & APIs
# =============================================================================

def test_set002_provider_lifecycle_and_secret_masking(db):
    repo = SettingsRepository(db)

    # 1. Create provider with secret
    provider = repo.create_provider(
        provider_id="prov-openai",
        name="OpenAI Primary",
        api_format="openai",
        base_url="https://api.openai.com/v1",
        api_key="sk-secret-token-123456789",
        request_timeout_seconds=45,
    )
    assert provider["id"] == "prov-openai"
    assert provider["api_key_masked"] == "sk-s****6789"
    assert "api_key_ciphertext" not in provider

    # 2. Get provider includes secret only when requested
    safe = repo.get_provider("prov-openai", include_secret=False)
    assert safe["api_key_masked"] == "sk-s****6789"
    with_sec = repo.get_provider("prov-openai", include_secret=True)
    assert with_sec["api_key_ciphertext"] == "sk-secret-token-123456789"

    # 3. Update provider
    updated = repo.update_provider("prov-openai", name="OpenAI Dedicated", request_timeout_seconds=90)
    assert updated["name"] == "OpenAI Dedicated"
    assert updated["request_timeout_seconds"] == 90

    # 4. Duplicate name conflict
    with pytest.raises(ResourceConflictError):
        repo.create_provider("prov-2", name="OpenAI Dedicated", api_format="openai", base_url="https://x")


def test_set002_models_and_referential_integrity(db):
    repo = SettingsRepository(db)
    repo.create_provider("prov-1", "Provider 1", "openai", "https://api.com")

    # Create model
    model = repo.create_model(
        model_id="mod-gpt",
        provider_id="prov-1",
        name="GPT-5",
        model_identifier="gpt-5.6-sol",
        max_output_tokens=4096,
        temperature=0.5,
    )
    assert model["id"] == "mod-gpt"
    assert model["temperature"] == 0.5

    # Cannot delete provider when model references it
    with pytest.raises(InUseError):
        repo.delete_provider("prov-1")

    # Delete model then provider succeeds
    repo.delete_model("mod-gpt")
    repo.delete_provider("prov-1")
    assert len(repo.list_providers()) == 0


def test_set002_roles_and_general_settings(db):
    repo = SettingsRepository(db)

    # Roles CRUD & Archive
    role = repo.create_role("role-writer", "Story Writer", "Writes narrative arcs")
    assert role["status"] == "active"

    repo.archive_role("role-writer")
    assert repo.get_role("role-writer")["status"] == "archived"

    repo.restore_role("role-writer")
    assert repo.get_role("role-writer")["status"] == "active"

    # General Settings
    general = repo.get_general_settings()
    assert general["default_task_timeout_seconds"] == 1800
    assert general["default_timezone"] == "Asia/Ho_Chi_Minh"

    updated = repo.update_general_settings({"default_task_timeout_seconds": 3600, "default_logs_lines": 500})
    assert updated["default_task_timeout_seconds"] == 3600
    assert updated["default_logs_lines"] == 500


def test_set002_http_routes(client):
    # Provider
    res = client.post(
        "/v1/settings/providers",
        json={
            "id": "p-1",
            "name": "Google Vertex",
            "api_format": "google",
            "base_url": "https://vertex.ai",
            "api_key": "secret-gemini-key-12345",
        },
    )
    assert res.status_code == 201
    assert res.json()["name"] == "Google Vertex"

    # Get provider returns api_key for edit form
    res_get = client.get("/v1/settings/providers/p-1")
    assert res_get.status_code == 200
    assert res_get.json()["api_key"] == "secret-gemini-key-12345"
    assert res_get.json()["api_key_masked"] == "secr****2345"

    # Direct Provider Connection Test - validation error on bad base_url
    res_bad = client.post(
        "/v1/settings/providers-test",
        json={"base_url": "ftp://bad-url", "api_format": "custom"},
    )
    assert res_bad.status_code == 422

    # Direct Provider Connection Test - connection failure returns reachable: false gracefully
    res_test = client.post(
        "/v1/settings/providers-test",
        json={
            "base_url": "https://127.0.0.1:59999/v1",
            "api_format": "custom",
            "api_key": "test-key",
            "request_timeout_seconds": 1,
        },
    )
    assert res_test.status_code == 200
    assert res_test.json()["reachable"] is False
    assert res_test.json()["ok"] is False

    # Direct Provider Connection Test - 200 OK response
    from unittest.mock import MagicMock, patch
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_stream_cm = MagicMock()
    mock_stream_cm.__enter__.return_value = mock_resp
    mock_stream_cm.__exit__.return_value = None

    with patch("httpx.Client.stream", return_value=mock_stream_cm):
        res_ok = client.post(
            "/v1/settings/providers-test",
            json={
                "base_url": "https://ai-gateway-dev.mbbank.com.vn/v1",
                "api_format": "custom",
                "api_key": "mock-valid-key",
            },
        )
        assert res_ok.status_code == 200
        assert res_ok.json()["reachable"] is True
        assert res_ok.json()["ok"] is True
        assert res_ok.json()["http_status"] == 200

    # Model
    res = client.post(
        "/v1/settings/models",
        json={"id": "m-1", "provider_id": "p-1", "name": "Gemini 3.8", "model_identifier": "gemini-3.8-pro"},
    )
    assert res.status_code == 201

    # Role
    res = client.post("/v1/settings/roles", json={"id": "r-pm", "name": "Project Manager"})
    assert res.status_code == 201

    # General
    res = client.put("/v1/settings/general", json={"default_task_timeout_seconds": 2400})
    assert res.status_code == 200
    assert res.json()["default_task_timeout_seconds"] == 2400


# =============================================================================
# SKL-001 & SKL-002: Skills, Tools, Versions & Dynamic Loading
# =============================================================================

def test_skl001_skl002_tools_and_skills_lifecycle(db):
    repo = SkillRepository(db)

    # 1. Tools CRUD & Archive
    tool = repo.create_tool(
        tool_id="tool-fs-read",
        name="Filesystem Read",
        description="Reads files safely",
        tool_type="internal",
        configuration={"allowed_paths": ["/data"]},
    )
    assert tool["id"] == "tool-fs-read"
    assert tool["configuration"]["allowed_paths"] == ["/data"]

    # 2. Skill creation
    skill = repo.create_skill(skill_id="skill-story", name="Story Generation")
    assert skill["status"] == "active"

    # 3. Draft Version with bound tool
    draft = repo.create_draft_version(
        version_id="ver-1",
        skill_id="skill-story",
        instructions="Generate a multi-part story",
        output_standards="Markdown format with scene headers",
        tool_ids=["tool-fs-read"],
    )
    assert draft["status"] == "draft"
    assert draft["version_number"] == 1
    assert "tool-fs-read" in draft["tool_ids"]

    # 4. Publishing computes bundle hash and seals immutability
    published = repo.publish_version("ver-1")
    assert published["status"] == "published"
    assert published["bundle_sha256"] is not None
    assert len(published["bundle_sha256"]) == 64

    # Trigger enforces: published version cannot be modified or deleted
    with pytest.raises(ResourceConflictError):
        repo.delete_draft_version("ver-1")


def test_skl001_dynamic_loader_from_directory(db):
    repo = SkillRepository(db)
    # Sync from repository's tests/.agents/skills
    skills_dir = Path(__file__).resolve().parents[5] / "tests" / ".agents" / "skills"
    if not skills_dir.exists():
        skills_dir = Path("tests/.agents/skills").resolve()

    synced = sync_skills_from_directory(skills_dir, repo)
    assert len(synced) >= 3

    # Check that skill 0 was discovered and published dynamically
    skills = repo.list_skills()
    skill_names = [s["name"] for s in skills]
    assert any("0.tao_cot_truyen" in s["id"] or "Cốt truyện" in s["name"] for s in skills)

    # Calling sync again is idempotent and does not duplicate
    synced_again = sync_skills_from_directory(skills_dir, repo)
    assert len(synced_again) == len(synced)


def test_skl002_http_routes(client):
    # Tool
    res = client.post("/v1/skills/tools", json={"id": "t-cli", "name": "CLI Exec", "tool_type": "cli"})
    assert res.status_code == 201

    # Skill
    res = client.post("/v1/skills", json={"id": "sk-test", "name": "Test Skill", "is_global": True})
    assert res.status_code == 201

    # Version
    res = client.post(
        "/v1/skills/sk-test/versions",
        json={"id": "v-1", "instructions": "Do something", "tool_ids": ["t-cli"]},
    )
    assert res.status_code == 201
    assert res.json()["status"] == "draft"

    # Publish
    res = client.post("/v1/skills/sk-test/versions/v-1/publish", json={})
    assert res.status_code == 200
    assert res.json()["status"] == "published"
    assert res.json()["bundle_sha256"] is not None


# =============================================================================
# AGN-003: Agent Catalog & Tool Permission Validation
# =============================================================================

def test_agn003_agent_lifecycle_and_tool_permission_enforcement(db):
    settings_repo = SettingsRepository(db)
    skill_repo = SkillRepository(db)
    agent_repo = AgentRepository(db)

    # Setup prerequisites: Provider, Model, Role, Tool, Skill
    settings_repo.create_provider("prov-1", "Provider", "openai", "https://api")
    settings_repo.create_model("mod-1", "prov-1", "Model 1", "gpt-model")
    settings_repo.create_role("role-author", "Author", "Story author")

    tool_req = skill_repo.create_tool("tool-search", "Search Tool")
    tool_other = skill_repo.create_tool("tool-shell", "Shell Tool")

    skill = skill_repo.create_skill("skill-research", "Research Skill")
    draft = skill_repo.create_draft_version(
        "ver-r1", "skill-research", "Research topic", tool_ids=["tool-search"]
    )
    skill_repo.publish_version("ver-r1")

    # 1. Violation: Agent has skill-research, but allowed_tools does NOT include tool-search!
    with pytest.raises(ResourceConflictError, match="requires tool"):
        agent_repo.create_agent(
            agent_id="agent-author",
            name="Research Agent",
            role_id="role-author",
            model_id="mod-1",
            skill_ids=["skill-research"],
            allowed_tool_ids=["tool-shell"],  # Missing tool-search!
        )

    # 2. Success: Agent includes tool-search in allowed_tools
    agent = agent_repo.create_agent(
        agent_id="agent-author",
        name="Research Agent",
        role_id="role-author",
        model_id="mod-1",
        skill_ids=["skill-research"],
        allowed_tool_ids=["tool-search", "tool-shell"],
    )
    assert agent["id"] == "agent-author"
    assert "tool-search" in agent["allowed_tool_ids"]

    # 3. Create immutable snapshot
    snapshot = agent_repo.create_agent_snapshot("agent-author")
    assert snapshot["agent_id"] == "agent-author"
    assert len(snapshot["snapshot_sha256"]) == 64
    assert snapshot["snapshot"]["role"]["name"] == "Author"

    # 4. Archive and Restore
    agent_repo.archive_agent("agent-author")
    assert agent_repo.get_agent("agent-author")["status"] == "archived"

    agent_repo.restore_agent("agent-author")
    assert agent_repo.get_agent("agent-author")["status"] == "active"


def test_agn003_http_routes(client):
    # Setup
    client.post("/v1/settings/providers", json={"id": "p-a", "name": "Prov A", "api_format": "openai", "base_url": "https://a"})
    client.post("/v1/settings/models", json={"id": "m-a", "provider_id": "p-a", "name": "Mod A", "model_identifier": "gpt"})
    client.post("/v1/settings/roles", json={"id": "r-a", "name": "Role A"})

    # Create Agent
    res = client.post(
        "/v1/agents",
        json={
            "id": "agent-1",
            "name": "Story Writer Agent",
            "role_id": "r-a",
            "model_id": "m-a",
            "instructions": "Write compelling fiction",
        },
    )
    assert res.status_code == 201
    assert res.json()["name"] == "Story Writer Agent"

    # Snapshot
    res = client.post("/v1/agents/agent-1/snapshot")
    assert res.status_code == 201
    assert res.json()["snapshot_sha256"] is not None

    # Archive
    res = client.post("/v1/agents/agent-1/archive")
    assert res.status_code == 200
    assert res.json()["status"] == "archived"
