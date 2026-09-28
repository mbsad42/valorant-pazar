"""Riot'un gayriresmi istemci API'si: çerez ile oturum yenileme + kişisel mağaza.

Şifre kullanılmaz. Sadece tarayıcıdan alınan oturum çerezleri (ssid vb.) yenilenir.
"""
import base64
import json
import os
import ssl
from urllib.parse import parse_qs, urlparse

import requests
from requests.adapters import HTTPAdapter

AUTH_URL = "https://auth.riotgames.com/authorize"
AUTH_PARAMS = {
    "redirect_uri": "https://playvalorant.com/opt_in",
    "client_id": "play-valorant-web-prod",
    "response_type": "token id_token",
    "nonce": "1",
    "scope": "account openid",
}
PLATFORM = base64.b64encode(json.dumps({
    "platformType": "PC",
    "platformOS": "Windows",
    "platformOSVersion": "10.0.19042.1.256.64bit",
    "platformChipset": "Unknown",
}).encode()).decode()
VP_ID = "85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741"
SKIN_LEVEL_TYPE = "e7c63390-eda7-46e0-bb7a-a6abdacd2433"
# Riot'un affinity değerinden pd sunucusuna
SHARD_MAP = {"latam": "na", "br": "na"}


class SessionExpired(Exception):
    """Çerezlerin süresi dolmuş; tarayıcıdan yenilerini alıp RIOT_COOKIES secret'ını güncelle."""


class _Adapter(HTTPAdapter):
    """Riot'un Cloudflare katmanı varsayılan Python TLS parmak izini bazen reddediyor."""

    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.set_ciphers(":".join([
            "ECDHE-ECDSA-AES128-GCM-SHA256", "ECDHE-ECDSA-CHACHA20-POLY1305",
            "ECDHE-RSA-AES128-GCM-SHA256", "ECDHE-RSA-CHACHA20-POLY1305",
            "ECDHE-ECDSA-AES256-GCM-SHA384", "ECDHE-RSA-AES256-GCM-SHA384",
        ]))
        kwargs["ssl_context"] = ctx
        super().init_poolmanager(*args, **kwargs)


def _jwt_claims(token):
    payload = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))


class RiotClient:
    def __init__(self, cookies):
        self.s = requests.Session()
        self.s.mount("https://", _Adapter())
        self.s.headers["User-Agent"] = "RiotClient/111.0.0.3261.5663 rso-auth (Windows;10;;Professional, x64)"
        self.cookies = dict(cookies)
        self.access = self.id_token = self.entitlement = self.puuid = self.shard = None

    def login(self):
        """ssid çerezleriyle yeni access token alır; dönen (yenilenmiş) çerezleri self.cookies'e yazar."""
        for k, v in self.cookies.items():
            self.s.cookies.set(k, v, domain="auth.riotgames.com", path="/")
        r = self.s.get(AUTH_URL, params=AUTH_PARAMS, allow_redirects=False, timeout=30)
        loc = r.headers.get("Location", "")
        if "access_token=" not in loc:
            raise SessionExpired(f"Oturum yenilenemedi (HTTP {r.status_code}, yönlendirme: {loc[:80]!r}).")
        frag = parse_qs(urlparse(loc).fragment)
        self.access = frag["access_token"][0]
        self.id_token = frag.get("id_token", [None])[0]
        for c in self.s.cookies:
            if c.domain.endswith("riotgames.com"):
                self.cookies[c.name] = c.value

        self.puuid = _jwt_claims(self.access)["sub"]
        r = self.s.post("https://entitlements.auth.riotgames.com/api/token/v1",
                        headers={"Authorization": f"Bearer {self.access}"}, json={}, timeout=30)
        r.raise_for_status()
        self.entitlement = r.json()["entitlements_token"]
        self.shard = self._find_shard()

    def _find_shard(self):
        forced = os.environ.get("RIOT_SHARD")
        if forced:
            return forced
        try:
            r = self.s.put("https://riot-geo.pas.si.riotgames.com/pas/v1/product/valorant",
                           headers={"Authorization": f"Bearer {self.access}"},
                           json={"id_token": self.id_token}, timeout=30)
            live = r.json()["affinities"]["live"]
            return SHARD_MAP.get(live, live)
        except Exception:
            return "eu"  # Türkiye

    def _headers(self):
        version = requests.get("https://valorant-api.com/v1/version", timeout=30).json()["data"]["riotClientVersion"]
        return {
            "Authorization": f"Bearer {self.access}",
            "X-Riot-Entitlements-JWT": self.entitlement,
            "X-Riot-ClientPlatform": PLATFORM,
            "X-Riot-ClientVersion": version,
        }

    def storefront(self):
        url = f"https://pd.{self.shard}.a.pvp.net/store/%s/storefront/{self.puuid}"
        h = self._headers()
        r = self.s.post(url % "v3", headers=h, json={}, timeout=30)
        if r.status_code in (404, 405):  # eski sürüm yedeği
            r = self.s.get(url % "v2", headers=h, timeout=30)
        r.raise_for_status()
        return r.json()

    def vp_balance(self):
        try:
            r = self.s.get(f"https://pd.{self.shard}.a.pvp.net/store/v1/wallet/{self.puuid}",
                           headers=self._headers(), timeout=30)
            return r.json()["Balances"].get(VP_ID)
        except Exception:
            return None
