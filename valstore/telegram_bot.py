"""Telegram'dan gelen komutları işler: /ekle, /sil, /liste, /ara, /yardim.

Sürekli açık bir sunucu değil — GitHub Actions tarafından birkaç dakikada bir
(telegram.yml) çalıştırılır, o ana kadar birikmiş mesajları bir kerede işler.
"""
import html
import json
import os

import requests

from . import catalog, store

OFFSET_FILE = catalog.DATA_DIR / "telegram_offset.json"
API = "https://api.telegram.org/bot{token}/{method}"

HELP = (
    "<b>Komutlar</b>\n"
    "/ekle &lt;skin adı&gt; — bekleme listesine ekle\n"
    "/sil &lt;skin adı&gt; — bekleme listesinden çıkar\n"
    "/liste — bekleme listeni göster\n"
    "/ara &lt;skin adı&gt; — skin ara (listeye eklemez)\n"
    "/yardim — bu mesaj"
)


def _token():
    t = os.environ.get("TELEGRAM_TOKEN")
    if not t:
        raise RuntimeError("TELEGRAM_TOKEN tanımlı değil.")
    return t


def _chat_id():
    c = os.environ.get("TELEGRAM_CHAT_ID")
    if not c:
        raise RuntimeError("TELEGRAM_CHAT_ID tanımlı değil.")
    return str(c)


def _call(method, **params):
    r = requests.get(API.format(token=_token(), method=method), params=params, timeout=30)
    r.raise_for_status()
    return r.json()["result"]


def _reply(chat_id, text):
    requests.post(API.format(token=_token(), method="sendMessage"),
                  json={"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
                  timeout=30)


def _load_offset():
    if OFFSET_FILE.exists():
        return json.loads(OFFSET_FILE.read_text(encoding="utf-8-sig")).get("offset", 0)
    return 0


def _save_offset(offset):
    OFFSET_FILE.parent.mkdir(parents=True, exist_ok=True)
    OFFSET_FILE.write_text(json.dumps({"offset": offset}), encoding="utf-8")


def _fmt(s, index):
    tier = catalog.dname(index.tier(s).get("name", "")).replace(" Edition", "")
    extra = f" · {tier}" if tier else ""
    return f"{html.escape(catalog.dname(s['name']))} ({html.escape(catalog.dname(s['weapon']))}{extra})"


def handle(text, index, wishlist):
    """(cevap metni ya da None, wishlist değişti mi) döner."""
    text = (text or "").strip()
    if not text.startswith("/"):
        return None, False
    parts = text.split(maxsplit=1)
    cmd = parts[0].lower().split("@")[0]  # /ekle@botadi -> /ekle
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd in ("/start", "/yardim", "/help"):
        return HELP, False

    if cmd == "/liste":
        items = [s for s in (index.skin(i) for i in wishlist) if s]
        if not items:
            return "Bekleme listen boş. /ekle &lt;skin adı&gt; ile ekleyebilirsin.", False
        lines = "\n".join(f"⭐ {_fmt(s, index)}" for s in sorted(items, key=lambda s: catalog.dname(s["name"])))
        return f"<b>Bekleme listen ({len(items)})</b>\n{lines}", False

    if cmd == "/ara":
        if not arg:
            return "Kullanım: /ara &lt;skin adı&gt;", False
        matches = index.search(arg)
        if not matches:
            return f"'{html.escape(arg)}' için sonuç yok.", False
        lines = "\n".join(f"{'⭐' if s['id'] in wishlist else '•'} {_fmt(s, index)}" for s in matches)
        return f"<b>Sonuçlar</b>\n{lines}", False

    if cmd == "/ekle":
        if not arg:
            return "Kullanım: /ekle &lt;skin adı&gt;", False
        matches = index.search(arg)
        if not matches:
            return f"'{html.escape(arg)}' bulunamadı.", False
        if len(matches) > 1:
            lines = "\n".join(f"• {_fmt(s, index)}" for s in matches)
            return f"Birden fazla eşleşme var, daha net yaz:\n{lines}", False
        s = matches[0]
        if s["id"] in wishlist:
            return f"{_fmt(s, index)} zaten listende.", False
        wishlist.add(s["id"])
        return f"⭐ Eklendi: {_fmt(s, index)}", True

    if cmd == "/sil":
        if not arg:
            return "Kullanım: /sil &lt;skin adı&gt;", False
        arg_en, arg_tr = arg.lower(), catalog.tr_lower(arg)
        matches = [s for s in (index.skin(i) for i in wishlist)
                   if s and (arg_en in s["name"]["en"].lower() or arg_tr in catalog.tr_lower(s["name"]["tr"]))]
        if not matches:
            return f"Listende '{html.escape(arg)}' ile eşleşen bir şey yok.", False
        if len(matches) > 1:
            lines = "\n".join(f"• {_fmt(s, index)}" for s in matches)
            return f"Birden fazla eşleşme var, daha net yaz:\n{lines}", False
        s = matches[0]
        wishlist.discard(s["id"])
        return f"Silindi: {_fmt(s, index)}", True

    return None, False  # tanınmayan komut, cevap verme


def main():
    cat = catalog.load()
    if not cat:
        print("Katalog yok, atlanıyor.")
        return
    index = catalog.Index(cat)
    wishlist = store.load_wishlist()
    chat_id = _chat_id()

    offset = _load_offset()
    updates = _call("getUpdates", offset=offset, timeout=0)
    if not updates:
        print("Yeni mesaj yok.")
        return

    changed = False
    for u in updates:
        offset = max(offset, u["update_id"] + 1)
        msg = u.get("message") or u.get("edited_message")
        if not msg or "text" not in msg:
            continue
        if str(msg["chat"]["id"]) != chat_id:
            print(f"Yetkisiz sohbet, yok sayıldı: {msg['chat']['id']}")
            continue
        reply, did_change = handle(msg["text"], index, wishlist)
        changed = changed or did_change
        if reply:
            _reply(msg["chat"]["id"], reply)

    _save_offset(offset)
    if changed:
        store.save_wishlist(wishlist)
        print("Bekleme listesi Telegram komutuyla güncellendi.")


if __name__ == "__main__":
    main()
