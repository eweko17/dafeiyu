"""把 state/secrets.json 裡的 Threads token 直接上傳到 GitHub Secrets。

用途：換完 60 天長效 token 後，不用手動複製貼上（避免貼錯、貼到斷行）。

用法（在「大肥魚」資料夾）：
    .\\.venv\\\\Scripts\\\\python.exe scripts\\\\push_token.py

需要：
    1. 已經跑過 scripts/token_helper.py（或 換Token.bat）
    2. GitHub Desktop 已登入（Windows 認證管理員裡有 GitHub token）
    3. 有裝 pynacl：python -m pip install pynacl
"""

from __future__ import annotations

import base64
import ctypes
import json
import re
import sys
from ctypes import wintypes
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
SECRETS = ROOT / "state" / "secrets.json"
GIT_CONFIG = ROOT / ".git" / "config"


# ---------- 讀 Windows 認證管理員 ----------


class _FILETIME(ctypes.Structure):
    _fields_ = [
        ("dwLowDateTime", wintypes.DWORD),
        ("dwHighDateTime", wintypes.DWORD),
    ]


class _CREDENTIAL(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", _FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_byte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


def _cred_read(target: str) -> str | None:
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    advapi32.CredReadW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.POINTER(_CREDENTIAL)),
    ]
    advapi32.CredReadW.restype = wintypes.BOOL
    advapi32.CredFree.argtypes = [ctypes.c_void_p]

    ptr = ctypes.POINTER(_CREDENTIAL)()
    if not advapi32.CredReadW(target, 1, 0, ctypes.byref(ptr)):
        return None
    try:
        cred = ptr.contents
        size = int(cred.CredentialBlobSize)
        if size <= 0:
            return None
        raw = ctypes.string_at(cred.CredentialBlob, size)
        return raw.decode("utf-8", errors="replace").strip()
    finally:
        advapi32.CredFree(ptr)


def _github_token(owner: str) -> str | None:
    targets = [
        f"GitHub - https://api.github.com/{owner}",
        "git:https://github.com",
        "GitHub - https://api.github.com",
    ]
    for target in targets:
        token = _cred_read(target)
        if token:
            return token
    return None


# ---------- 讀 repo ----------


def _repo() -> tuple[str, str]:
    if not GIT_CONFIG.exists():
        raise RuntimeError("找不到 .git/config，請確認在「大肥魚」資料夾裡執行。")
    text = GIT_CONFIG.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"url\s*=\s*\S*github\.com[/:]([^/\s]+)/([^/\s]+?)(?:\.git)?\s*$", text, re.M)
    if not match:
        raise RuntimeError("從 .git/config 讀不到 GitHub repo 網址。")
    return match.group(1), match.group(2)


# ---------- 主流程 ----------


def _check_threads(token: str) -> str:
    response = requests.get(
        "https://graph.threads.net/v1.0/me",
        params={"fields": "id,username", "access_token": token},
        timeout=30,
    )
    body = response.json() if response.content else {}
    if not response.ok or "error" in body:
        message = body.get("error", {}).get("message", response.text[:200])
        raise RuntimeError(f"Threads token 無效：{message}")
    return f"@{body.get('username')}（id={body.get('id')}）"


def main() -> int:
    if not SECRETS.exists():
        print("找不到 state/secrets.json。請先跑 換Token.bat。")
        return 1

    data = json.loads(SECRETS.read_text(encoding="utf-8"))
    token = str(data.get("threads_token", "")).strip()
    if not token:
        print("state/secrets.json 裡沒有 threads_token。請先跑 換Token.bat。")
        return 1

    print("先確認這串 token 在 Threads 那邊有效…")
    try:
        who = _check_threads(token)
    except Exception as exc:  # noqa: BLE001
        print(f"失敗：{exc}")
        print("如果是過期，請重新產生短效 token，再跑一次 換Token.bat。")
        return 1
    print(f"token 有效：{who}")

    try:
        owner, repo = _repo()
    except Exception as exc:  # noqa: BLE001
        print(f"失敗：{exc}")
        return 1

    gh = _github_token(owner)
    if not gh:
        print("讀不到 GitHub 登入憑證。請開 GitHub Desktop 確認已登入，或手動貼到 Secrets。")
        return 1

    headers = {
        "Authorization": f"Bearer {gh}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "dafeiyu-token-uploader",
    }

    print(f"準備上傳到 {owner}/{repo} …")
    try:
        response = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/public-key",
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        public = response.json()
    except Exception as exc:  # noqa: BLE001
        print(f"取得 GitHub 公鑰失敗：{exc}")
        return 1

    try:
        from nacl import encoding, public as nacl_public
    except ImportError:
        print("缺少 pynacl，請執行：.venv\\Scripts\\python.exe -m pip install pynacl")
        return 1

    sealed = nacl_public.SealedBox(
        nacl_public.PublicKey(base64.b64decode(public["key"]))
    )
    encrypted = base64.b64encode(sealed.encrypt(token.encode("utf-8"))).decode()

    try:
        response = requests.put(
            f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/THREADS_TOKEN",
            headers=headers,
            json={"encrypted_value": encrypted, "key_id": public["key_id"]},
            timeout=30,
        )
        response.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        print(f"上傳失敗：{exc}")
        return 1

    print("已更新 GitHub Secrets 的 THREADS_TOKEN。")

    try:
        listing = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/actions/secrets",
            headers=headers,
            timeout=30,
        ).json()
        for item in listing.get("secrets", []):
            if item.get("name") == "THREADS_TOKEN":
                print(f"GitHub 記錄的更新時間：{item.get('updated_at')}")
    except Exception:  # noqa: BLE001
        pass

    print()
    print("完成。接下來可以到 GitHub 跑 doctor 確認。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
