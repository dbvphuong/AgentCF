"""Source and frozen entrypoint. Kept free of Server imports."""

from pathlib import Path
import sys

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def main(argv=None):
    import argparse
    import json
    import logging
    import os
    parser = argparse.ArgumentParser(description="CF Client")
    parser.add_argument("--connect")
    parser.add_argument("--desktop", action="store_true")
    parser.add_argument("--background", action="store_true")
    parser.add_argument("--self-check", help="Write a non-secret packaging diagnostic JSON")
    args = parser.parse_args(argv)
    if os.environ.get("AGENT_CF_CLIENT_EXE"):
        # CPython is already initialized with its bundled library. Restore the user's
        # environment before launching CLI/tools so other Python installations and
        # user-site dependencies are not redirected into the Client's private runtime.
        for key in ("PYTHONHOME", "PYTHONNOUSERSITE"):
            original = os.environ.pop("AGENT_CF_ORIGINAL_" + key, None)
            if original is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original
    if sys.platform != "win32":
        raise RuntimeError("CF Client desktop currently requires Windows")
    from agent_cf_client.desktop.windows import profile_dir, installed_exe, SingleInstance
    from agent_cf_client.desktop.links import parse_connection_link
    if args.connect:
        parse_connection_link(args.connect)  # Validate before IPC, registry or network activity.
    folder = profile_dir()
    folder.mkdir(parents=True, exist_ok=True)
    os.environ["NO_PROXY"] = os.environ.get("NO_PROXY", "") + ",127.0.0.1,localhost,::1"
    logging.basicConfig(filename=str(folder / "client.log"), level=logging.WARNING, encoding="utf-8")
    import tkinter as tk
    import customtkinter as ctk
    root = ctk.CTk()
    if args.self_check:
        from agent_cf_client.connection.credentials import protect
        from agent_cf_client.runtime.codex_adapter import CodexAdapter
        from agent_cf_client.runtime.antigravity_adapter import AntigravityAdapter
        assert protect(protect(b"test"), decrypt=True) == b"test"
        Path(args.self_check).write_text(json.dumps({"status": "ok", "tk": tk.TkVersion, "packaged": bool(os.environ.get("AGENT_CF_CLIENT_EXE")), "codex": CodexAdapter().is_available(), "antigravity": AntigravityAdapter().is_available()}), encoding="utf-8")
        root.destroy()
        return 0
    from agent_cf_client.desktop.app import ClientWindow
    instance = SingleInstance(folder)
    if not instance.owner:
        instance.notify(args.connect)
        instance.close()
        root.destroy()
        return 0
    try:
        ClientWindow(root, folder, args.connect, args.background)
        root.mainloop()
    finally:
        instance.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
