"""Riot oturum çerezleri şifreli olarak repoya yazılır (Riot her yenilemede çerezleri döndürür).

Repo herkese açık olabilir çünkü state/session.enc, STATE_KEY olmadan okunamaz.
"""
import base64
import hashlib
import json
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

STATE_FILE = Path(__file__).resolve().parent.parent / "state" / "session.enc"


class NoCookies(Exception):
    pass


def _fernet():
    key = os.environ.get("STATE_KEY")
    if not key:
        raise RuntimeError("STATE_KEY tanımlı değil (GitHub Secrets'a ekle).")
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest()))


def parse_cookie_header(header):
    cookies = {}
    for part in header.split(";"):
        if "=" in part:
            k, v = part.strip().split("=", 1)
            cookies[k] = v
    return cookies


def _hash(text):
    return hashlib.sha256(text.encode()).hexdigest()


def load_cookies():
    """Şifreli state varsa onu, yoksa (ya da RIOT_COOKIES secret'ı değiştirildiyse) secret'ı kullanır."""
    bootstrap = (os.environ.get("RIOT_COOKIES") or "").strip()
    if STATE_FILE.exists():
        try:
            st = json.loads(_fernet().decrypt(STATE_FILE.read_bytes()))
            if not bootstrap or st.get("bootstrap_hash") == _hash(bootstrap):
                return st["cookies"]
        except InvalidToken:
            print("Uyarı: state/session.enc çözülemedi (STATE_KEY değişmiş olabilir), RIOT_COOKIES kullanılacak.")
    if not bootstrap:
        raise NoCookies("RIOT_COOKIES secret'ı tanımlı değil.")
    return parse_cookie_header(bootstrap)


def save_cookies(cookies):
    bootstrap = (os.environ.get("RIOT_COOKIES") or "").strip()
    payload = {"cookies": cookies, "bootstrap_hash": _hash(bootstrap) if bootstrap else None}
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_bytes(_fernet().encrypt(json.dumps(payload).encode()))
