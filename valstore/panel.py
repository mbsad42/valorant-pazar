"""Web panelini yerelde açar: python -m valstore.panel  →  http://localhost:8765
Bekleme listesi kaydı doğrudan docs/data/wishlist.json'a yazılır (GitHub gerekmez)."""
import json
import threading
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"
PORT = 8765


class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/api/wishlist":
            return self.send_error(404)
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            skins = [str(s) for s in body["skins"]]
            (DOCS / "data" / "wishlist.json").write_text(json.dumps({"skins": skins}, indent=1), encoding="utf-8")
            self.send_response(204)
            self.end_headers()
        except Exception as e:
            self.send_error(400, str(e))

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *a):
        pass


def main():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), partial(Handler, directory=str(DOCS)))
    url = f"http://localhost:{PORT}/"
    print(f"Panel açık: {url}   (kapatmak için bu pencereyi kapat)")
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
