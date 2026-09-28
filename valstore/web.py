"""Sunucuda (PythonAnywhere vb.) paneli yayınlayan WSGI uygulaması.

Panel dosyalarını docs/ klasöründen sunar. Bekleme listesi kaydı (POST /api/wishlist) için
config.env içindeki PANEL_TOKEN ile aynı değer 'X-Panel-Token' başlığında gelmelidir.
"""
import hmac
import json
import mimetypes
import os
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"


def _respond(start_response, status, body=b"", ctype="text/plain; charset=utf-8", extra=()):
    start_response(status, [("Content-Type", ctype), ("Content-Length", str(len(body))),
                            ("Cache-Control", "no-store"), *extra])
    return [body]


def application(environ, start_response):
    method, path = environ["REQUEST_METHOD"], environ.get("PATH_INFO", "/")

    if method == "POST" and path == "/api/wishlist":
        expected = os.environ.get("PANEL_TOKEN", "")
        given = environ.get("HTTP_X_PANEL_TOKEN", "")
        if not expected or not hmac.compare_digest(expected, given):
            return _respond(start_response, "403 Forbidden", b"panel sifresi yanlis")
        try:
            size = int(environ.get("CONTENT_LENGTH") or 0)
            skins = [str(s) for s in json.loads(environ["wsgi.input"].read(size))["skins"]]
            (DOCS / "data" / "wishlist.json").write_text(json.dumps({"skins": skins}, indent=1), encoding="utf-8")
        except Exception as e:
            return _respond(start_response, "400 Bad Request", str(e).encode())
        return _respond(start_response, "204 No Content")

    if method not in ("GET", "HEAD"):
        return _respond(start_response, "405 Method Not Allowed")
    target = (DOCS / path.lstrip("/")).resolve()
    if target.is_dir():
        target /= "index.html"
    if DOCS.resolve() not in target.parents or not target.is_file():
        return _respond(start_response, "404 Not Found", b"bulunamadi")
    ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    if ctype.startswith("text/") or ctype == "application/json":
        ctype += "; charset=utf-8"
    return _respond(start_response, "200 OK", b"" if method == "HEAD" else target.read_bytes(), ctype)
