"""Storefront yanıtını sadeleştirir, geçmişe yazar, bekleme listesini kontrol eder, bildirim yollar."""
import datetime as dt
import html
import json

from . import catalog, notify
from .riot import SKIN_LEVEL_TYPE, VP_ID

HISTORY_FILE = catalog.DATA_DIR / "history.json"
WISHLIST_FILE = catalog.DATA_DIR / "wishlist.json"
MONTHS = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]


def _vp(cost):
    return (cost or {}).get(VP_ID)


def parse(raw, now=None):
    """Riot'un ham yanıtından kalıcı kaydı üretir."""
    now = now or dt.datetime.now(dt.timezone.utc)
    panel = raw.get("SkinsPanelLayout", {})
    ends_in = panel.get("SingleItemOffersRemainingDurationInSeconds", 0)
    # Pazar 00:00 UTC'de yenilenir; kayıt tarihi = mevcut dönemin başladığı gün
    date = (now + dt.timedelta(seconds=ends_in) - dt.timedelta(days=1)).date().isoformat()

    prices = {o["OfferID"]: _vp(o.get("Cost")) for o in panel.get("SingleItemStoreOffers", [])}
    daily = [{"offer": oid, "price": prices.get(oid)} for oid in panel.get("SingleItemOffers", [])]

    bundles = []
    fb = raw.get("FeaturedBundle") or {}
    for b in fb.get("Bundles") or ([fb["Bundle"]] if fb.get("Bundle") else []):
        items = []
        for it in b.get("Items") or []:
            item = it.get("Item", {})
            items.append({"type": item.get("ItemTypeID"), "id": item.get("ItemID")})
        if not items:
            for offer in b.get("ItemOffers") or []:
                for rw in offer.get("Offer", {}).get("Rewards", []):
                    items.append({"type": rw.get("ItemTypeID"), "id": rw.get("ItemID")})
        bundles.append({
            "id": b.get("DataAssetID"),
            "price": b.get("TotalBaseCost", {}).get(VP_ID) if isinstance(b.get("TotalBaseCost"), dict) else None,
            "discounted": b.get("TotalDiscountedCost", {}).get(VP_ID) if isinstance(b.get("TotalDiscountedCost"), dict) else None,
            "percent": b.get("TotalDiscountPercent"),
            "ends_in": b.get("DurationRemainingInSeconds"),
            "skins": [i["id"] for i in items if i["type"] == SKIN_LEVEL_TYPE],
            "other_items": sum(1 for i in items if i["type"] != SKIN_LEVEL_TYPE),
        })

    night = None
    bonus = raw.get("BonusStore")
    if bonus:
        night = {"ends_in": bonus.get("BonusStoreRemainingDurationInSeconds"), "items": [
            {"offer": o["Offer"]["OfferID"], "price": _vp(o["Offer"].get("Cost")),
             "discounted": _vp(o.get("DiscountCosts")), "percent": o.get("DiscountPercent")}
            for o in bonus.get("BonusStoreOffers", [])]}

    return {"date": date, "fetched_at": now.isoformat(timespec="seconds"),
            "daily": {"ends_in": ends_in, "items": daily}, "bundles": bundles, "night_market": night}


def _read(path, default):
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else default


def load_history():
    return _read(HISTORY_FILE, [])


def save_history(history):
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def load_wishlist():
    return set(_read(WISHLIST_FILE, {"skins": []}).get("skins", []))


def record(rec):
    """Kaydı geçmişe ekler. Bugünün pazarı zaten kayıtlıysa güncellenir; True dönerse yeni gündür."""
    history = load_history()
    same_day = [i for i, h in enumerate(history) if h["date"] == rec["date"]]
    is_new = not same_day or (
        [x["offer"] for x in history[same_day[0]]["daily"]["items"]] != [x["offer"] for x in rec["daily"]["items"]])
    if same_day:
        history[same_day[0]] = rec
    else:
        history.append(rec)
    history.sort(key=lambda h: h["date"])
    save_history(history)
    return is_new


def unresolved(rec, index):
    ids = [x["offer"] for x in rec["daily"]["items"]]
    ids += [x["offer"] for x in (rec["night_market"] or {}).get("items", [])]
    return [i for i in ids if not index.skin(i)]


def _dur(sec):
    if not sec:
        return "?"
    d, rem = divmod(int(sec), 86400)
    h, rem = divmod(rem, 3600)
    m = rem // 60
    return ((f"{d} gün " if d else "") + (f"{h} sa " if h else "") + (f"{m} dk" if not d else "")).strip()


def _name(index, any_id):
    s = index.skin(any_id)
    return s["name"] if s else f"Bilinmeyen skin ({any_id[:8]})"


def _star(index, any_id, wishlist):
    s = index.skin(any_id)
    return " ⭐" if s and s["id"] in wishlist else ""


def wishlist_hits(rec, index, wishlist):
    hits = []
    places = [("günlük pazar", x["offer"], x["price"]) for x in rec["daily"]["items"]]
    if rec["night_market"]:
        places += [("Night Market", x["offer"], x["discounted"] or x["price"]) for x in rec["night_market"]["items"]]
    for b in rec["bundles"]:
        places += [(f"vitrin seti ({index.bundle_name(b['id']) or 'set'})", sid, None) for sid in b["skins"]]
    for where, oid, price in places:
        s = index.skin(oid)
        if s and s["id"] in wishlist:
            hits.append((where, s, price))
    return hits


def notify_day(rec, index, wishlist, vp=None):
    d = dt.date.fromisoformat(rec["date"])
    for where, s, price in wishlist_hits(rec, index, wishlist):
        cost = f" — <b>{price} VP</b>" if price else ""
        notify.send_photo(s["icon"], f"🚨 <b>BEKLEDİĞİN SKİN PAZARDA!</b>\n{html.escape(s['name'])}{cost}\n📍 {where}")

    lines = [f"🛒 <b>Valorant pazarı</b> · {d.day} {MONTHS[d.month - 1]}"]
    photos = []
    for n, x in enumerate(rec["daily"]["items"], 1):
        s = index.skin(x["offer"])
        tier = index.tier(s).get("name", "")
        lines.append(f"{n}. <b>{html.escape(_name(index, x['offer']))}</b> · {x['price']} VP"
                     f"{' · ' + tier if tier else ''}{_star(index, x['offer'], wishlist)}")
        photos.append(s["icon"] if s else None)
    lines.append(f"⏳ Yenilenmeye: {_dur(rec['daily']['ends_in'])}")

    for b in rec["bundles"]:
        name = index.bundle_name(b["id"]) or "Vitrin seti"
        price = b["discounted"] or b["price"]
        lines.append(f"\n🎁 <b>{html.escape(name)}</b>" + (f" · {price} VP" if price else "")
                     + f" · {_dur(b['ends_in'])} kaldı")
    if rec["night_market"] and rec["night_market"]["items"]:
        lines.append(f"\n🌙 <b>Night Market</b> ({_dur(rec['night_market']['ends_in'])} kaldı)")
        for x in rec["night_market"]["items"]:
            lines.append(f"• {html.escape(_name(index, x['offer']))} · {x['discounted']} VP "
                         f"(-%{x['percent']}){_star(index, x['offer'], wishlist)}")
    if vp is not None:
        lines.append(f"\n💰 {vp} VP")
    notify.send_album(photos, "\n".join(lines))


def notify_new_skins(added):
    if not added:
        return
    names = "\n".join(f"• {html.escape(s['name'])}" for s in added[:25])
    more = f"\n… ve {len(added) - 25} tane daha" if len(added) > 25 else ""
    notify.send_text(f"🆕 <b>Kataloğa {len(added)} yeni skin eklendi</b>\n{names}{more}")
