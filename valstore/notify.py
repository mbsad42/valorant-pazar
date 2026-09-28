"""Telegram bildirimleri. Token yoksa mesajlar sadece ekrana yazılır (yerel test)."""
import os

import requests


def _configured():
    return os.environ.get("TELEGRAM_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID")


def _call(method, **payload):
    token, chat = os.environ["TELEGRAM_TOKEN"], os.environ["TELEGRAM_CHAT_ID"]
    r = requests.post(f"https://api.telegram.org/bot{token}/{method}",
                      json={"chat_id": chat, "parse_mode": "HTML", **payload}, timeout=30)
    if not r.ok:
        raise RuntimeError(f"Telegram {method}: {r.status_code} {r.text[:200]}")


def send_text(text):
    if not _configured():
        print("--- [Telegram yok, ekrana yazıldı] ---\n" + text + "\n")
        return
    _call("sendMessage", text=text, disable_web_page_preview=True)


def send_photo(url, caption):
    if not _configured():
        print(f"--- [foto: {url}] ---\n{caption}\n")
        return
    try:
        _call("sendPhoto", photo=url, caption=caption)
    except RuntimeError:
        send_text(caption)


def send_album(urls, caption):
    """Görselli albüm; başarısız olursa düz metne düşer."""
    urls = [u for u in urls if u][:10]
    if not _configured() or len(urls) < 2:
        return send_text(caption)
    media = [{"type": "photo", "media": u, **({"caption": caption, "parse_mode": "HTML"} if i == 0 else {})}
             for i, u in enumerate(urls)]
    try:
        _call("sendMediaGroup", media=media)
    except RuntimeError:
        send_text(caption)
