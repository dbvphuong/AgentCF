"""GUI/HTTP integration probe against an isolated Server; never invokes a model.

The browser test writes a short-lived link to ARTIFACT_DIR/connect-link.txt. This probe
uses the same preview/confirm callbacks as the desktop UI and drains on stop-client.
"""
import json
import os
from pathlib import Path
import time
import tkinter as tk
from tkinter import ttk

from agent_cf_client.desktop.app import ClientWindow


def main():
    folder = Path(os.environ["ARTIFACT_DIR"]).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    os.environ["AGENT_CF_CLIENT_HOME"] = str(folder / "profile")
    os.environ["NO_PROXY"] = "127.0.0.1,localhost"
    root = tk.Tk()
    app = ClientWindow(root)
    def descendants(widget):
        for child in widget.winfo_children():
            yield child
            yield from descendants(child)
    assert not any(isinstance(widget, ttk.Entry) for widget in descendants(root)), "Main Client must not expose editable Server/PC settings"
    started = time.monotonic()
    loaded = confirmed = False
    def tick():
        nonlocal loaded, confirmed
        if time.monotonic()-started > 45:
            app.request_exit()
        path = folder/"connect-link.txt"
        if not loaded and path.is_file():
            app.accept_link(path.read_text(encoding="utf-8"))
            loaded = True
        if app.preview_key and not app.operation and not confirmed:
            app.connect()
            confirmed = True
        if app.daemon and app.daemon.busy:
            raise AssertionError("Onboarding probe must never execute work/models")
        if app.manager.current_session_id:
            result = {"previewed": bool(app.preview_key is None and confirmed), "tray": app.tray.available, "connected": True, "compact": True}
            (folder/"desktop-result.json").write_text(json.dumps(result), encoding="utf-8")
        if (folder/"stop-client").exists():
            app.request_exit()
        if not app.closing:
            root.after(100, tick)
    root.after(100, tick)
    root.mainloop()


if __name__ == "__main__":
    main()
