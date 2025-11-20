import os
import hashlib
import json
import time
import threading
import requests

API_BASE = os.getenv("LICENSE_API_BASE", "http://127.0.0.1:8010")

def _sha256_hex(s: str):
    salt = os.getenv("LICENSE_SALT", "dev-salt-change")
    return hashlib.sha256((s + salt).encode()).hexdigest()

def get_machine_guid() -> str:
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography")
        val, _ = winreg.QueryValueEx(key, "MachineGuid")
        return str(val)
    except Exception:
        return os.getenv("COMPUTERNAME", "UNKNOWN")

def get_machine_hash() -> str:
    return _sha256_hex(get_machine_guid())

def activate(license_key: str, machine_hash: str):
    url = f"{API_BASE}/licenses/activate"
    r = requests.post(url, json={"license_key": license_key, "machine_hash": machine_hash, "app_version": "ui"}, timeout=10)
    r.raise_for_status()
    return r.json()

def validate(license_key: str, machine_hash: str):
    url = f"{API_BASE}/licenses/validate"
    r = requests.post(url, json={"license_key": license_key, "machine_hash": machine_hash}, timeout=10)
    r.raise_for_status()
    return r.json()

def heartbeat(license_id: int, machine_hash: str, session_token: str):
    url = f"{API_BASE}/sessions/heartbeat"
    r = requests.post(url, json={"license_id": license_id, "machine_hash": machine_hash, "session_token": session_token}, timeout=10)
    r.raise_for_status()
    return r.json()

def end_session(license_id: int, machine_hash: str, session_token: str):
    url = f"{API_BASE}/sessions/end"
    r = requests.post(url, json={"license_id": license_id, "machine_hash": machine_hash, "session_token": session_token}, timeout=10)
    # 若服务端暂未实现该接口，返回404，不抛出致命错误
    if r.status_code == 404:
        return {"status": "UNSUPPORTED"}
    r.raise_for_status()
    return r.json()

def save_license_state(data: dict, path: str = "license_state.json"):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass

def load_license_state(path: str = "license_state.json") -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

class HeartbeatThread(threading.Thread):
    def __init__(self, license_id: int, machine_hash: str, session_token: str, interval: int = 30):
        super().__init__(daemon=True)
        self.license_id = license_id
        self.machine_hash = machine_hash
        self.session_token = session_token
        self.interval = interval
        self._stop = False

    def run(self):
        while not self._stop:
            try:
                heartbeat(self.license_id, self.machine_hash, self.session_token)
            except Exception:
                pass
            time.sleep(self.interval)

    def stop(self):
        self._stop = True
