# Valorant Pazarım: sunucuda kurulum (PythonAnywhere)

Bilgisayarın kapalıyken bile çalışır. PythonAnywhere, Python kodunu internette senin yerine çalıştıran bir servis.
Ücretli **Developer** planı gerekiyor (yaklaşık 10 $/ay), çünkü ücretsiz planda Riot'a bağlanmaya izin yok.

Önce **SETUP-LOKAL.md**'deki **1. adım (Telegram botu)** ve **2. adım (Riot çerezleri)** ile token, chat id ve çerez satırını hazırla.

## 1. Hesap
1. https://www.pythonanywhere.com → **Pricing & signup** → **Create a Beginner account** ile kaydol (kullanıcı adını sen seçersin, örn. `valpazar`)
2. Sağ üstte **Account** → **Upgrade** → **Developer** planını seç ve ödemeyi yap

## 2. Dosyaları yükle
1. Üst menüden **Files** sekmesi
2. Sağdaki **Upload a file** → Masaüstü\a klasöründeki `valorant-pazar.zip`

## 3. Aç ve kur
1. **Consoles** sekmesi → **Bash** (yeni konsol)
2. Sırayla çalıştır:
   ```
   unzip valorant-pazar.zip -d valorant-pazar
   cd valorant-pazar
   python3 -m pip install --user -r requirements.txt
   ```

## 4. Ayar dosyası
1. **Files** sekmesi → `valorant-pazar` klasörü → **New file** kutusuna `config.env` yaz → **New file**
2. Açılan editöre şunu yapıştır, değerleri doldur (`=` sonrası boşluksuz), **Save**:
   ```
   RIOT_COOKIES=çerez satırının tamamı
   STATE_KEY=rastgele 40 karakterlik metin
   TELEGRAM_TOKEN=BotFather token'ı
   TELEGRAM_CHAT_ID=chat id sayısı
   PANEL_TOKEN=panel için uydurduğun bir şifre
   ```

## 5. Dene
Bash konsolunda:
```
cd ~/valorant-pazar
python3 -m valstore --test-notify
python3 -m valstore --force
```
İlkinde telefonuna "✅ Valorant pazar botu çalışıyor" gelmeli. İkincisi pazarını çekip Telegram'a yollar.
Hata çıkarsa çıktıyı bana ilet.

## 6. Her gün otomatik çalışsın
**Tasks** sekmesi → **Scheduled tasks**. Saat **UTC** olarak girilir (Türkiye saatinden 3 saat geri). İki görev ekle:

| Saat (UTC) | Komut |
|---|---|
| `00:07` | `cd ~/valorant-pazar && python3 -m valstore >> ~/pazar-log.txt 2>&1` |
| `01:47` | aynı komut (yedek; ilki başarılıysa atlar) |

## 7. Web paneli
1. **Web** sekmesi → **Add a new web app** → **Next** → **Manual configuration** → Python sürümü (listedeki en yeni) → **Next**
2. Sayfada **WSGI configuration file** bağlantısına tıkla, içindeki her şeyi silip şunu yaz (`KULLANICI` yerine kullanıcı adın):
   ```python
   import sys
   sys.path.insert(0, "/home/KULLANICI/valorant-pazar")
   from valstore.web import application
   ```
3. Kaydet → **Web** sekmesine dön → yeşil **Reload** düğmesi
4. Panel adresin: `https://KULLANICI.pythonanywhere.com`

Bekleme listesini panelde kaydederken, **Bekleme listesi** sekmesindeki "Panel şifresi" alanına `config.env` içindeki `PANEL_TOKEN` değerini bir kez gir.

## Sorun olursa
- **"Oturum yenilenemedi" mesajı:** çerezlerin süresi dolmuş. Riot çerezlerini yeniden al, `config.env` içindeki `RIOT_COOKIES` satırını değiştir. Bot her gün çerezleri yenilediği için nadiren gerekir.
- **Günlük:** `~/pazar-log.txt` dosyasında çalışma çıktıları durur.
- **Riot sunucu IP'lerini engellerse:** bu resmi olmayan bir API. Bunu ancak ilk gerçek çalıştırma gösterir.
