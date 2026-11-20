"""Windows Client should not prefer a stale npm wrapper over the IDE CLI."""
from pathlib import Path

from agent_cf_client.runtime import codex_adapter


def test_native_cli_precedes_npm_wrapper(monkeypatch):
    monkeypatch.setattr(codex_adapter.sys,"platform","win32")
    monkeypatch.setattr(codex_adapter.shutil,"which",lambda name: {"codex.exe":"native.exe","codex.cmd":"old.cmd"}.get(name))
    assert codex_adapter.CodexAdapter()._executable=="native.exe"
    assert codex_adapter.CodexAdapter(executable_path="configured.exe")._executable=="configured.exe"


def test_ide_cli_is_found_without_editor_path_environment(tmp_path, monkeypatch):
    monkeypatch.setattr(codex_adapter.sys,"platform","win32")
    monkeypatch.setattr(Path,"home",lambda:tmp_path)
    monkeypatch.setattr(codex_adapter.shutil,"which",lambda name:"old.cmd" if name=="codex.cmd" else None)
    def binary(version):
        path=tmp_path / ".vscode/extensions" / f"openai.chatgpt-{version}" / "bin/windows-x86_64/codex.exe"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"fixture")
        return path
    binary("26.9.1")
    current=binary("26.10.1")
    assert codex_adapter.CodexAdapter()._executable==str(current)


def test_npm_wrapper_remains_available_when_native_cli_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(codex_adapter.sys,"platform","win32")
    monkeypatch.setattr(Path,"home",lambda:tmp_path)
    monkeypatch.setattr(codex_adapter.shutil,"which",lambda name:"wrapper.cmd" if name=="codex.cmd" else None)
    assert codex_adapter.CodexAdapter()._executable=="wrapper.cmd"
