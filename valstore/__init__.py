"""config.env dosyası varsa (yerel çalıştırma) içindeki KEY=VALUE satırlarını ortam değişkeni olarak yükler."""
import os
from pathlib import Path


def _load_env():
    f = Path(__file__).resolve().parent.parent / "config.env"
    if not f.exists():
        return
    for line in f.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            v = v.strip()
            if len(v) > 1 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            if v:
                os.environ.setdefault(k.strip(), v)


_load_env()
