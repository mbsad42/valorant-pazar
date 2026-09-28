# Valorant Pazarım: kurulum

Her gün 03:07'de (Türkiye) GitHub sunucusu pazarını çeker, kaydeder, Telegram'dan sana yollar.
Bilgisayarının açık olması gerekmez.

## 1. GitHub reposu
1. github.com'da hesap aç / giriş yap → **New repository**
2. Ad: `valorant-pazar`, görünürlük: **Public** (ücretsiz web paneli için gerekli; Riot çerezlerin şifreli saklanır, aşağıya bak)
3. Repo açılınca **uploading an existing file** bağlantısı → bu klasörün **içindekileri** (`.github`, `docs`, `valstore`, `requirements.txt`, `.gitignore`) sürükle-bırak → **Commit changes**

## 2. Telegram botu
1. Telegram'da `@BotFather` → `/newbot` → isim ver → sana bir **token** verir (`123456:ABC...`)
2. Yeni botuna girip **Start**'a bas, bir mesaj yaz
3. Tarayıcıda `https://api.telegram.org/bot<TOKEN>/getUpdates` aç → `"chat":{"id":123456789` içindeki sayı senin **chat id**'n

## 3. Şifreleme anahtarı
Rastgele uzun bir metin uydur (örn. 40 karakter). Bu `STATE_KEY` olacak. Riot çerezlerini repoda şifrelemek için kullanılır.

## 4. Riot çerezleri (en önemli adım)
Chrome/Edge ile:
1. account.riotgames.com'a giriş yap, **Beni hatırla** işaretli olsun
2. `F12` → **Network** sekmesi açıkken yeni sekmede `https://auth.riotgames.com/` adresine git
3. Network'te `auth.riotgames.com` isteğine tıkla → **Request Headers** → `cookie:` satırının **tamamını** kopyala

> ⚠️ Bu çerezler şifre gibidir (2FA'yı da atlar). Sadece GitHub Secrets'a yapıştır, kimseyle paylaşma, ekran görüntüsüne alma.

## 5. GitHub Secrets
Repo → **Settings → Secrets and variables → Actions → New repository secret**. 4 tane ekle:

| Ad | Değer |
|---|---|
| `RIOT_COOKIES` | 4. adımdaki cookie satırı |
| `STATE_KEY` | 3. adımdaki metin |
| `TELEGRAM_TOKEN` | BotFather token'ı |
| `TELEGRAM_CHAT_ID` | chat id |

İsteğe bağlı **Variables** sekmesinde: `RIOT_SHARD` (varsayılan otomatik, Türkiye için `eu`), `VAL_LANG` (skin adları dili: `en-US` varsayılan, Türkçe için `tr-TR`).

## 6. Dene
Repo → **Actions** → (gerekirse etkinleştir) → **Günlük pazar** → **Run workflow**:
1. `telegram-test` seç → telefonuna mesaj gelmeli
2. `normal` seç → pazarın Telegram'a gelmeli, `docs/data/history.json` oluşmalı

## 7. Web paneli
Repo → **Settings → Pages** → Source: *Deploy from a branch*, Branch: `main`, klasör `/docs` → Save.
Adres: `https://KULLANICI.github.io/valorant-pazar/` (telefonda ana ekrana ekleyebilirsin).

## 8. Bekleme listesi
Panelde **Tüm skinler** sekmesinde ☆ ile skin işaretle, **Bekleme listesi** sekmesinden kaydet.
Kaydetmek için bir kez: GitHub → Settings → Developer settings → **Fine-grained tokens** → sadece bu repo, **Contents: Read and write** → token'ı panelde ayara yapıştır.
(Alternatif: `docs/data/wishlist.json` dosyasını GitHub'da elle düzenle: `{"skins": ["skin-uuid", ...]}`.)

## Sorun olursa
- **"Oturum yenilenemedi" mesajı gelirse:** çerezlerin süresi dolmuş. 4. adımı tekrarla, `RIOT_COOKIES` secret'ını güncelle. Botun sürekli çalışması çerezleri kendiliğinden yeniler, bu nadir olmalı.
- **Riot GitHub sunucularını engellerse:** aynı kod evdeki bilgisayarda veya Raspberry Pi'de de çalışır: `pip install -r requirements.txt`, ortam değişkenlerini ayarla, `python -m valstore` komutunu zamanlanmış görev olarak çalıştır.
- **Riot endpoint'i değiştirirse:** bu, resmi olmayan bir API. Bozulursa `valstore/riot.py` güncellenir.

## Güvenlik notu
`state/session.enc` `STATE_KEY` olmadan okunamaz. Yine de `STATE_KEY`'i kimseyle paylaşma. Repo herkese açık olduğu için pazar geçmişin ve bekleme listen görünür (hesap bilgin görünmez).
