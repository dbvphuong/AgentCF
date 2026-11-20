"""Stable Windows installation identity and DPAPI-protected Client proof, never hostname identity."""

import hashlib
import json
import secrets
from . import windows
from agent_cf_client.connection.credentials import protect


def machine_identity():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            value = winreg.QueryValueEx(key, "MachineGuid")[0]
        return "device-" + hashlib.sha256(("agentcf-device-v1:" + str(value).lower()).encode()).hexdigest()
    except OSError:
        return None


def device_identity(folder=None):
    folder = folder or windows.profile_dir()
    path = folder / "device-identity.dpapi"
    if path.exists():
        value = json.loads(protect(path.read_bytes(), decrypt=True))
        if not isinstance(value, dict) or not isinstance(value.get('device_id'), str) or not isinstance(value.get('device_key'), str):
            raise ValueError("Thông tin định danh Client không hợp lệ")
        return value
    value = {"device_id": machine_identity() or "device-" + secrets.token_hex(32), "device_key": secrets.token_hex(32)}
    folder.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_bytes(protect(json.dumps(value).encode()))
    temp.replace(path)
    return value
