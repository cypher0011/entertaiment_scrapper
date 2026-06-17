#!/usr/bin/env python3
"""
Dream CRM Server
- Serves index.html on port 8787
- Auto-saves CRM data to data/crm_backup.json on every save
- Run: python3 server.py
"""
import http.server
import json
import os
import shutil
from datetime import datetime

PORT     = 8787
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CRM_FILE = os.path.join(BASE_DIR, "data", "crm_backup.json")
PITCHES_FILE = os.path.join(BASE_DIR, "data", "crm_pitches.json")


class Handler(http.server.SimpleHTTPRequestHandler):

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length)

        if self.path == "/save-crm":
            self._save_json(CRM_FILE, body)
            self._respond(200, "saved")

        elif self.path == "/save-pitches":
            self._save_json(PITCHES_FILE, body)
            self._respond(200, "saved")

        elif self.path == "/load-crm":
            data = self._load_json(CRM_FILE)
            self._respond(200, data, content_type="application/json")

        elif self.path == "/load-pitches":
            data = self._load_json(PITCHES_FILE)
            self._respond(200, data, content_type="application/json")

        else:
            self._respond(404, "not found")

    def _save_json(self, path, raw_bytes):
        try:
            parsed = json.loads(raw_bytes)
            # Keep rolling backup (last 5)
            if os.path.exists(path):
                ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
                bak = path.replace(".json", f"_{ts}.json")
                shutil.copy2(path, bak)
                # Delete old backups, keep latest 5
                base = os.path.basename(path).replace(".json", "")
                backups = sorted([
                    f for f in os.listdir(os.path.dirname(path))
                    if f.startswith(base + "_") and f.endswith(".json")
                ])
                for old in backups[:-5]:
                    os.remove(os.path.join(os.path.dirname(path), old))
            with open(path, "w", encoding="utf-8") as f:
                json.dump(parsed, f, ensure_ascii=False, indent=2)
            print(f"  ✅ Saved → {os.path.basename(path)}")
        except Exception as e:
            print(f"  ❌ Save error: {e}")

    def _load_json(self, path):
        if not os.path.exists(path):
            return "{}"
        with open(path, encoding="utf-8") as f:
            return f.read()

    def _respond(self, code, body, content_type="text/plain"):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, fmt, *args):
        # Suppress GET noise, show only CRM saves
        if "/save-crm" in args[0] or "/save-pitches" in args[0] or "/load" in args[0]:
            super().log_message(fmt, *args)


if __name__ == "__main__":
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    os.chdir(BASE_DIR)
    print(f"🚀 Dream CRM running at http://localhost:{PORT}")
    print(f"📁 CRM backup → {CRM_FILE}")
    print(f"   Press Ctrl+C to stop\n")
    http.server.HTTPServer(("", PORT), Handler).serve_forever()
