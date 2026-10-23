"""Tanıtım videosu için görsel ve videoları indirir: görseller küçültülüp WebP'ye çevrilir,
videolar ilk 10 saniyeye kırpılıp 720p'ye indirilir. Hangi videoda ses kanalı olduğu da kaydedilir."""
import json
import subprocess
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image

out = Path("assets")
manifest = {}
for url in Path("urls.txt").read_text().split():
    p = urlparse(url)
    dest = out / p.netloc / p.path.lstrip("/")
    dest = dest.with_suffix(".webp")
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        im = Image.open(BytesIO(r.content))
        im.thumbnail((1400, 1400))
        im.save(dest, "WEBP", quality=90, method=6)
        manifest[url] = {"path": str(dest), "type": "image/webp", "size": im.size}
    except Exception as e:  # tek bir görsel yüzünden iş durmasın
        print("HATA", url, e)

for url in Path("videos.txt").read_text().split():
    p = urlparse(url)
    raw = Path("raw.mp4")
    raw.write_bytes(requests.get(url, timeout=120).content)
    probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(raw)],
                                      capture_output=True, text=True).stdout)
    audio = [s for s in probe["streams"] if s["codec_type"] == "audio"]
    video = next(s for s in probe["streams"] if s["codec_type"] == "video")
    dest = out / p.netloc / p.path.lstrip("/")
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-t", "10", "-vf", "scale=-2:720",
                    "-c:v", "libx264", "-crf", "22", "-preset", "slow", "-c:a", "aac", "-b:a", "160k", str(dest)], check=True)
    loud = None
    if audio:  # ses kanalı var ama sessiz mi? ortalama seviyeyi ölç
        vd = subprocess.run(["ffmpeg", "-v", "info", "-i", str(raw), "-af", "volumedetect", "-f", "null", "-"],
                            capture_output=True, text=True).stderr
        loud = [l.split("] ")[-1] for l in vd.splitlines() if "mean_volume" in l or "max_volume" in l]
    manifest[url] = {"path": str(dest), "type": "video/mp4", "audio_streams": len(audio), "levels": loud,
                     "duration": video.get("duration"), "size": [video["width"], video["height"]]}
    print(url, "ses kanalı:", len(audio), loud)
    raw.unlink()

Path("assets/manifest.json").write_text(json.dumps(manifest, indent=1))
print(len(manifest), "dosya")
