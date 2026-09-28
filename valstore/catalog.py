"""Tüm skin verisi: valorant-api.com topluluk API'sinden çekilir, docs/data/skins.json'a yazılır."""
import datetime as dt
import json
import os
from pathlib import Path

import requests

API = "https://valorant-api.com/v1"
LANG = os.environ.get("VAL_LANG", "en-US")  # oyun dilin Türkçe ise: tr-TR
DATA_DIR = Path(__file__).resolve().parent.parent / "docs" / "data"
SKINS_FILE = DATA_DIR / "skins.json"


def _get(path):
    r = requests.get(f"{API}/{path}", params={"language": LANG}, timeout=60)
    r.raise_for_status()
    return r.json()["data"]


def _icon(skin):
    if skin.get("displayIcon"):
        return skin["displayIcon"]
    for lv in skin.get("levels") or []:
        if lv.get("displayIcon"):
            return lv["displayIcon"]
    for ch in skin.get("chromas") or []:
        if ch.get("fullRender") or ch.get("displayIcon"):
            return ch.get("fullRender") or ch.get("displayIcon")
    return None


def build():
    weapons = _get("weapons")
    tiers = _get("contenttiers")
    themes = {t["uuid"]: t["displayName"] for t in _get("themes")}
    bundles = _get("bundles")
    version = requests.get(f"{API}/version", timeout=30).json()["data"]

    skins = []
    for w in weapons:
        for s in w.get("skins") or []:
            # "Standard ..." ve "Random Favorite Skin" satın alınamayan varsayılan skinler
            if not s.get("contentTierUuid") or s["displayName"].startswith(("Standard", "Random")):
                continue
            levels = s.get("levels") or []
            skins.append({
                "id": s["uuid"],
                "name": s["displayName"],
                "weapon": w["displayName"],
                "tier": s["contentTierUuid"],
                "theme": themes.get(s.get("themeUuid")),
                "icon": _icon(s),
                "levels": [lv["uuid"] for lv in levels],
                "chromas": max(len(s.get("chromas") or []) - 1, 0),
                "video": next((lv["streamedVideo"] for lv in reversed(levels) if lv.get("streamedVideo")), None),
            })
    skins.sort(key=lambda s: (s["weapon"], s["name"]))

    return {
        "updated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "language": LANG,
        "game_version": version["riotClientVersion"],
        "tiers": {t["uuid"]: {"name": t["displayName"], "rank": t["rank"], "color": t["highlightColor"], "icon": t["displayIcon"]}
                  for t in tiers},
        "bundles": {b["uuid"]: {"name": b["displayName"], "icon": b.get("displayIcon"), "image": b.get("verticalPromoImage")}
                    for b in bundles},
        "skins": skins,
    }


def load():
    if SKINS_FILE.exists():
        return json.loads(SKINS_FILE.read_text(encoding="utf-8"))
    return None


def refresh():
    """Kataloğu yeniler; eklenen skinleri döner: (katalog, [yeni skinler])."""
    old = load()
    new = build()
    old_ids = {s["id"] for s in old["skins"]} if old else set()
    added = [s for s in new["skins"] if s["id"] not in old_ids] if old else []
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SKINS_FILE.write_text(json.dumps(new, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return new, added


class Index:
    """Offer/level/skin UUID'sinden skine ulaşmak için."""

    def __init__(self, catalog):
        self.catalog = catalog
        self.by_any = {}
        for s in catalog["skins"]:
            self.by_any[s["id"]] = s
            for lv in s["levels"]:
                self.by_any[lv] = s

    def skin(self, any_id):
        return self.by_any.get(any_id)

    def tier(self, skin):
        return self.catalog["tiers"].get(skin["tier"], {}) if skin else {}

    def bundle_name(self, bundle_id):
        return self.catalog["bundles"].get(bundle_id, {}).get("name")
