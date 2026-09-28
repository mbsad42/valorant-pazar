"""Tüm skin verisi: valorant-api.com topluluk API'sinden hem İngilizce hem Türkçe çekilir, birleştirilip
docs/data/skins.json'a yazılır. Her isim {"en": ..., "tr": ...} şeklinde iki dilli tutulur."""
import datetime as dt
import json
import os
from pathlib import Path

import requests

API = "https://valorant-api.com/v1"
LANGS = ("en-US", "tr-TR")
NOTIFY_LANG = os.environ.get("NOTIFY_LANG", "tr")  # Telegram mesajlarında kullanılacak dil
DATA_DIR = Path(__file__).resolve().parent.parent / "docs" / "data"
SKINS_FILE = DATA_DIR / "skins.json"


def tr_lower(s):
    """Türkçe'de büyük I'nın küçüğü noktasız ı'dır (İngilizce kurallarından farklı); str.lower() bunu bilmez."""
    return s.replace("İ", "i").replace("I", "ı").lower()


def dname(d):
    """İki dilli {"en":..,"tr":..} sözlüğünden bildirim dilini seçer."""
    if not isinstance(d, dict):
        return d
    return d.get(NOTIFY_LANG) or d.get("en") or next(iter(d.values()), "")


def _get(path, lang):
    r = requests.get(f"{API}/{path}", params={"language": lang}, timeout=60)
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


def _build_raw(lang):
    """Tek dil için ham veri: uuid'e göre indekslenmiş skin/tier/bundle."""
    weapons = _get("weapons", lang)
    tiers = _get("contenttiers", lang)
    bundles = _get("bundles", lang)
    themes = {t["uuid"]: t["displayName"] for t in _get("themes", lang)}

    skins = {}
    for w in weapons:
        for s in w.get("skins") or []:
            # "Standard ..." ve "Random Favorite Skin" satın alınamayan varsayılan skinler
            if not s.get("contentTierUuid") or s["displayName"].startswith(("Standard", "Random")):
                continue
            levels = s.get("levels") or []
            skins[s["uuid"]] = {
                "name": s["displayName"], "weapon": w["displayName"], "tier": s["contentTierUuid"],
                "theme": themes.get(s.get("themeUuid")),
                "icon": _icon(s), "levels": [lv["uuid"] for lv in levels],
                "chromas": max(len(s.get("chromas") or []) - 1, 0),
                "video": next((lv["streamedVideo"] for lv in reversed(levels) if lv.get("streamedVideo")), None),
            }
    return {
        "skins": skins,
        "tiers": {t["uuid"]: {"name": t["displayName"], "rank": t["rank"], "color": t["highlightColor"], "icon": t["displayIcon"]}
                  for t in tiers},
        "bundles": {b["uuid"]: {"name": b["displayName"], "icon": b.get("displayIcon"), "image": b.get("verticalPromoImage")}
                    for b in bundles},
    }


def _merge(en, tr, key, fields, bi_fields=()):
    """en/tr ham verilerindeki bir koleksiyonu (skins/tiers/bundles) iki dilli tek sözlüğe birleştirir.
    bi_fields: name gibi ayrıca iki dilli tutulacak (None olabilen) alanlar, örn. "weapon", "theme"."""
    out = {}
    for uid, e in en[key].items():
        t = tr[key].get(uid, e)
        item = {"name": {"en": e["name"], "tr": t.get("name", e["name"])}}
        for f in fields:
            item[f] = e[f]
        for bf in bi_fields:
            ev = e.get(bf)
            item[bf] = {"en": ev, "tr": t.get(bf) or ev} if ev is not None else None
        out[uid] = item
    return out


def build():
    en = _build_raw("en-US")
    tr = _build_raw("tr-TR")
    version = requests.get(f"{API}/version", timeout=30).json()["data"]

    skins_d = _merge(en, tr, "skins", ["tier", "icon", "levels", "chromas", "video"], bi_fields=("weapon", "theme"))
    tiers_d = _merge(en, tr, "tiers", ["rank", "color", "icon"])
    bundles_d = _merge(en, tr, "bundles", ["icon", "image"])

    skins = [{"id": uid, **data} for uid, data in skins_d.items()]
    skins.sort(key=lambda s: (s["weapon"]["en"], s["name"]["en"]))

    return {
        "updated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "languages": list(LANGS),
        "game_version": version["riotClientVersion"],
        "tiers": tiers_d,
        "bundles": bundles_d,
        "skins": skins,
    }


def load():
    if SKINS_FILE.exists():
        return json.loads(SKINS_FILE.read_text(encoding="utf-8-sig"))
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
        b = self.catalog["bundles"].get(bundle_id)
        return dname(b["name"]) if b else None

    def search(self, query, limit=8):
        """İsimde (İngilizce ya da Türkçe) geçen metne göre skin arar; tam eşleşme varsa tek sonuç döner."""
        q = (query or "").strip()
        if not q:
            return []
        q_en, q_tr = q.lower(), tr_lower(q)

        def names(s):
            return (s["name"]["en"].lower(), tr_lower(s["name"]["tr"]))

        def hit(s):
            en, tr = names(s)
            return q_en in en or q_tr in tr

        exact = [s for s in self.catalog["skins"] if names(s)[0] == q_en or names(s)[1] == q_tr]
        if exact:
            return exact
        matches = [s for s in self.catalog["skins"] if hit(s)]
        matches.sort(key=lambda s: (not (names(s)[0].startswith(q_en) or names(s)[1].startswith(q_tr)),
                                     min(len(n) for n in names(s))))
        return matches[:limit]
