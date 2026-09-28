"""Kullanım:
    python -m valstore                     günlük iş: pazarı çek, kaydet, bildir
    python -m valstore --catalog-only      sadece skin kataloğunu yenile
    python -m valstore --test-notify       Telegram'ı dene
    python -m valstore --fixture x.json    Riot'a bağlanmadan kayıtlı bir storefront yanıtıyla dene
"""
import argparse
import datetime as dt
import json
import sys
import traceback

from . import catalog, notify, state, store
from .riot import RiotClient, SessionExpired


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog-only", action="store_true")
    ap.add_argument("--test-notify", action="store_true")
    ap.add_argument("--fixture")
    ap.add_argument("--force", action="store_true", help="son 6 saatte çekilmiş olsa bile yeniden çek")
    args = ap.parse_args()

    if args.test_notify:
        notify.send_text("✅ Valorant pazar botu çalışıyor. Bildirimler bu sohbete gelecek.")
        return 0

    try:
        cat, added = catalog.refresh()
        print(f"Katalog: {len(cat['skins'])} skin, sürüm {cat['game_version']}, yeni: {len(added)}")
    except Exception as e:  # katalog yenilenemese de eski katalogla devam edilir
        print(f"Katalog yenilenemedi: {e}")
        cat, added = catalog.load(), []
        if not cat:
            raise
    if args.catalog_only:
        store.notify_new_skins(added)
        return 0

    if not (args.force or args.fixture):  # oturum açılışı gibi sık tetiklerde Riot'u gereksiz yormamak için
        last = (store.load_history() or [None])[-1]
        if last and (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(last["fetched_at"])).total_seconds() < 6 * 3600:
            print("Pazar son 6 saat içinde zaten çekilmiş, atlanıyor (--force ile zorla).")
            return 0

    vp = None
    try:
        if args.fixture:
            raw = json.load(open(args.fixture, encoding="utf-8"))
        else:
            client = RiotClient(state.load_cookies())
            try:
                client.login()
            finally:
                state.save_cookies(client.cookies)  # Riot çerezleri yeniler; hata olsa da sakla
            raw = client.storefront()
            vp = client.vp_balance()
    except (SessionExpired, state.NoCookies) as e:
        notify.send_text(f"⚠️ <b>Valorant pazarı çekilemedi</b>\n{e}\n\n"
                         "Tarayıcıdan yeni Riot çerezlerini alıp GitHub'daki RIOT_COOKIES secret'ını güncelle (SETUP.md, 5. adım).")
        return 1
    except Exception as e:
        traceback.print_exc()
        notify.send_text(f"⚠️ <b>Valorant pazarı çekilemedi</b>\n{type(e).__name__}: {e}")
        return 1

    index = catalog.Index(cat)
    rec = store.parse(raw)
    if store.unresolved(rec, index):  # yeni çıkmış skin: katalog henüz eski olabilir
        cat, more = catalog.refresh()
        added += more
        index = catalog.Index(cat)
    is_new = store.record(rec)
    store.notify_new_skins(added)
    if is_new:
        store.notify_day(rec, index, store.load_wishlist(), vp)
    else:
        print("Bugünün pazarı zaten kayıtlı, bildirim gönderilmedi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
