# Valorant Pazarım: GitHub'sız (bilgisayarda) kurulum

Uygulama bilgisayarında çalışır. Her gece 03:07'de ve her Windows oturum açılışında pazarını çeker, Telegram'a yollar.
GitHub, hesap ya da sunucu gerekmez. Python zaten kurulu.

**Bilmen gereken tek sınır:** Bilgisayar 03:07'de kapalıysa görev, bilgisayarı açtığın anda çalışır (o an bildirim gelir). Bilgisayar uyku modundaysa görev onu uyandırır. Yani bildirimin gecikmesi, bilgisayarı ne zaman açtığına bağlı.

## 1. Telegram botu
1. Telegram'da **@BotFather**'ı ara → `/newbot` → isim ve `_bot` ile biten kullanıcı adı seç
2. BotFather'ın verdiği **token**'ı kopyala (`123456:ABC-DEF...`)
3. Kendi botunu ara, **Start**'a bas, ona "merhaba" yaz
4. Tarayıcıda `https://api.telegram.org/botTOKEN/getUpdates` aç (TOKEN yerine kendi token'ın)
5. `"chat":{"id":123456789` içindeki **sayı** senin chat id'n

## 2. Riot çerezleri
1. Chrome veya Edge'de https://account.riotgames.com adresine giriş yap, **Beni hatırla** işaretli olsun
2. `F12` → **Network** sekmesi → aynı sekmede https://auth.riotgames.com/ adresine git
3. Listede `auth.riotgames.com` satırına tıkla → **Request Headers** → `cookie:` satırının **tamamını** kopyala

Bu çerezler şifre gibidir. Ekran görüntüsü alma, kimseyle paylaşma, bana da yapıştırma.

## 3. Ayar dosyası
1. `kur.bat` dosyasına çift tıkla. İlk seferde `config.env` dosyasını oluşturup Not Defteri'nde açar.
2. Dosyayı doldur (`=` işaretinden sonra, boşluksuz):
   - `RIOT_COOKIES=` → 2. adımdaki satır
   - `STATE_KEY=` → rastgele uzun bir metin (klavyeye basarak 40 karakter)
   - `TELEGRAM_TOKEN=` → 1. adımdaki token
   - `TELEGRAM_CHAT_ID=` → 1. adımdaki sayı
3. Kaydet, Not Defteri'ni kapat.

## 4. Kur
`kur.bat` dosyasına tekrar çift tıkla. Sırasıyla:
1. gerekli paketleri yükler
2. Telegram'a deneme mesajı yollar (telefonuna "✅ Valorant pazar botu çalışıyor" gelmeli)
3. "ValorantPazar" adlı Windows görevini oluşturur (her gün 03:07 + her oturum açılışı)
4. pazarını hemen bir kez çeker; Telegram'a gelir

Bir adım hata verirse pencerede ne yazdığını bana ilet.

## 5. Web paneli
`panel.bat` dosyasına çift tıkla. Tarayıcıda panel açılır (`http://localhost:8765`).
- **Bugün**: günün pazarı, vitrin seti, Night Market, kalan süre
- **Geçmiş**: önceki günlerin pazarları
- **Tüm skinler**: arama ve filtre; ☆ ile bekleme listene ekle
- **Bekleme listesi**: **Kaydet** düğmesine bas. Bot artık bu skinleri pazarda arar ve bulursa 🚨 uyarısı yollar.

Panel yalnızca sen `panel.bat`'ı açıkken çalışır; kapatınca pencereyi kapatman yeterli. Bildirimler panelden bağımsızdır.

## Sorun olursa
- **"Oturum yenilenemedi" mesajı gelirse:** çerezlerin süresi dolmuş. 2. adımı tekrarla, `config.env` içindeki `RIOT_COOKIES` satırını yenisiyle değiştir. Bot her gün çerezleri yenilediği için nadiren gerekir.
- **Kayıtlar:** Çalışma günlüğü `pazar-log.txt` dosyasında tutulur.
- **Görevi silmek için:** Görev Zamanlayıcı'da "ValorantPazar" → Sil.
- **Riot endpoint'i değiştirirse:** resmi olmayan bir API, bozulursa `valstore/riot.py` güncellenir.

## İleride
Bilgisayarın hep açık olmasını istemezsen kodu GitHub'a taşımak mümkün (`SETUP.md`). GitHub hesabına erişimin dönünce bunu birlikte yaparız.
