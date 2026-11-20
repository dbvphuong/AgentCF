CREATE TABLE providers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE CHECK(length(trim(name)) > 0),
    api_format TEXT NOT NULL CHECK(api_format IN ('openai', 'anthropic', 'google', 'custom')),
    base_url TEXT NOT NULL CHECK(length(trim(base_url)) > 0),
    api_key_ciphertext TEXT,
    request_timeout_seconds INTEGER NOT NULL DEFAULT 60 CHECK(request_timeout_seconds > 0 AND request_timeout_seconds <= 300),
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'disabled')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
) STRICT;

CREATE TABLE models (
    id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL REFERENCES providers(id),
    name TEXT NOT NULL CHECK(length(trim(name)) > 0),
    model_identifier TEXT NOT NULL CHECK(length(trim(model_identifier)) > 0),
    max_output_tokens INTEGER CHECK(max_output_tokens IS NULL OR max_output_tokens > 0),
    temperature REAL DEFAULT 0.7 CHECK(temperature >= 0.0 AND temperature <= 2.0),
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'disabled')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE(provider_id, model_identifier)
) STRICT;

CREATE TABLE roles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE CHECK(length(trim(name)) > 0),
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'archived')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
) STRICT;

CREATE TABLE general_settings (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL CHECK(json_valid(value_json)),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
) STRICT;

CREATE TABLE tools (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE CHECK(length(trim(name)) > 0),
    description TEXT NOT NULL DEFAULT '',
    tool_type TEXT NOT NULL CHECK(tool_type IN ('cli', 'api', 'internal')),
    configuration_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(configuration_json)),
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'archived')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
) STRICT;

CREATE TABLE skills (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE CHECK(length(trim(name)) > 0),
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'archived')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
) STRICT;

CREATE TABLE skill_versions (
    id TEXT PRIMARY KEY,
    skill_id TEXT NOT NULL REFERENCES skills(id),
    version_number INTEGER NOT NULL CHECK(version_number > 0),
    status TEXT NOT NULL CHECK(status IN ('draft', 'published')),
    instructions TEXT NOT NULL,
    output_standards TEXT NOT NULL DEFAULT '',
    bundle_sha256 TEXT CHECK(bundle_sha256 IS NULL OR (length(bundle_sha256) = 64 AND bundle_sha256 NOT GLOB '*[^a-f0-9]*')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    published_at TEXT,
    UNIQUE(skill_id, version_number),
    CHECK(status = 'draft' OR (bundle_sha256 IS NOT NULL AND published_at IS NOT NULL))
) STRICT;

CREATE UNIQUE INDEX one_draft_per_skill ON skill_versions(skill_id) WHERE status = 'draft';

CREATE TABLE skill_version_tools (
    skill_version_id TEXT NOT NULL REFERENCES skill_versions(id),
    tool_id TEXT NOT NULL REFERENCES tools(id),
    PRIMARY KEY(skill_version_id, tool_id)
) STRICT;

CREATE TRIGGER immutable_published_skill_version_update BEFORE UPDATE ON skill_versions
WHEN OLD.status = 'published'
BEGIN
    SELECT RAISE(ABORT, 'published_skill_version_immutable');
END;

CREATE TRIGGER immutable_published_skill_version_delete BEFORE DELETE ON skill_versions
WHEN OLD.status = 'published'
BEGIN
    SELECT RAISE(ABORT, 'published_skill_version_immutable');
END;

CREATE TRIGGER immutable_published_skill_tool_insert BEFORE INSERT ON skill_version_tools
WHEN (SELECT status FROM skill_versions WHERE id = NEW.skill_version_id) = 'published'
BEGIN
    SELECT RAISE(ABORT, 'published_skill_version_immutable');
END;

CREATE TRIGGER immutable_published_skill_tool_delete BEFORE DELETE ON skill_version_tools
WHEN (SELECT status FROM skill_versions WHERE id = OLD.skill_version_id) = 'published'
BEGIN
    SELECT RAISE(ABORT, 'published_skill_version_immutable');
END;

CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE CHECK(length(trim(name)) > 0),
    role_id TEXT NOT NULL REFERENCES roles(id),
    model_id TEXT NOT NULL REFERENCES models(id),
    instructions TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'archived')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
) STRICT;

CREATE TABLE agent_skills (
    agent_id TEXT NOT NULL REFERENCES agents(id),
    skill_id TEXT NOT NULL REFERENCES skills(id),
    PRIMARY KEY(agent_id, skill_id)
) STRICT;

CREATE TABLE agent_allowed_tools (
    agent_id TEXT NOT NULL REFERENCES agents(id),
    tool_id TEXT NOT NULL REFERENCES tools(id),
    PRIMARY KEY(agent_id, tool_id)
) STRICT;

CREATE TABLE agent_snapshots (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL REFERENCES agents(id),
    snapshot_sha256 TEXT NOT NULL CHECK(length(snapshot_sha256) = 64 AND snapshot_sha256 NOT GLOB '*[^a-f0-9]*'),
    snapshot_json TEXT NOT NULL CHECK(json_valid(snapshot_json)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE(agent_id, snapshot_sha256)
) STRICT;
