#!/usr/bin/env python3
"""Local dev server for the dice-fit calibration tool.

Serves the module folder statically AND exposes `POST /bake`, which saves the
posted calibration JSON to data/calibration.json and bakes the textures — so the
ENTIRE flow runs from the browser interface (adjust -> click "Zapisz i wypal").
The only step left to you is reloading the world in Foundry.

This avoids the File System Access API, which Windows blocks inside AppData
("system files"): the server writes files through the normal filesystem.

    python tools/serve.py
    # then open http://localhost:8777/tools/dice-fit/index.html
"""
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import bake_calibration as bc

MODULE = Path(__file__).resolve().parent.parent
PORT = 8777


class Handler(SimpleHTTPRequestHandler):
    def _json(self, status, obj):
        payload = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        if self.path.rstrip("/") != "/bake":
            self._json(404, {"ok": False, "error": "not found"})
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            calib = json.loads(self.rfile.read(n).decode("utf-8"))
            (MODULE / "data" / "calibration.json").write_text(
                json.dumps(calib, indent=2) + "\n", encoding="utf-8"
            )
            self._json(200, {"ok": True, **bc.bake()})
        except Exception as e:  # noqa: BLE001 — report any failure to the browser
            self._json(500, {"ok": False, "error": str(e)})

    def log_message(self, *args):
        pass  # quieter console


if __name__ == "__main__":
    handler = partial(Handler, directory=str(MODULE))
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    print(f"Serwuję {MODULE}")
    print(f"Otwórz: http://localhost:{PORT}/tools/dice-fit/index.html")
    print("Ctrl+C aby zatrzymać.")
    httpd.serve_forever()
