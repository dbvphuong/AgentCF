"""Per-user installation, URL registration, startup and single instance on Windows."""

import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4


def profile_dir() -> Path:
    return Path(os.environ.get("AGENT_CF_CLIENT_HOME") or Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "AgentCF")


def installed_exe() -> Path:
    return profile_dir() / "Client" / "CF Client.exe"


def command() -> list[str]:
    packaged = os.environ.get("AGENT_CF_CLIENT_EXE")
    if packaged and Path(packaged).is_file():
        return [packaged]
    if getattr(sys, "frozen", False):
        return [str(Path(sys.executable).resolve())]
    return [str(Path(sys.executable).with_name("pythonw.exe")), str(Path(__file__).with_name("entry.py").resolve())]


def register_protocol(argv=None):
    import winreg
    argv = argv or command()
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\agentcf") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "URL:Agent CF Client")
        winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\agentcf\shell\open\command") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, subprocess.list2cmdline(argv) + ' --connect "%1"')


def set_startup(enabled: bool):
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
        if enabled:
            winreg.SetValueEx(key, "CF Client", 0, winreg.REG_SZ, subprocess.list2cmdline([*command(), "--background"]))
        else:
            try:
                winreg.DeleteValue(key, "CF Client")
            except FileNotFoundError:
                pass


def startup_enabled() -> bool:
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
            return bool(winreg.QueryValueEx(key, "CF Client")[0])
    except FileNotFoundError:
        return False



class SingleInstance:
    def __init__(self, folder: Path):
        self.folder = folder
        self.folder.mkdir(parents=True, exist_ok=True)
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
        self.kernel.CreateMutexW.restype = ctypes.c_void_p
        self.kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        name = "Local\\AgentCFClient-" + hashlib.sha256(str(folder.resolve()).encode()).hexdigest()[:24]
        self.handle = self.kernel.CreateMutexW(None, False, name)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        self.owner = ctypes.get_last_error() != 183

    def notify(self, link=None):
        # Owned per-user inbox, data only. A second launch never starts another worker/session.
        inbox = self.folder / "requests"
        inbox.mkdir(exist_ok=True)
        path = inbox / (str(uuid4()) + ".json")
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"link": link}), encoding="utf-8")
        temporary.replace(path)

    def close(self):
        self.kernel.CloseHandle(self.handle)
