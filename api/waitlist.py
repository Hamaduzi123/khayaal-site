"""
POST /api/waitlist
Body: { "email": "user@example.com", "source": "landing" }

Stores waitlist signups via the Vercel KV store if KV_REST_API_URL/KV_REST_API_TOKEN
are set. Otherwise, accepts the signup and returns success (logs to function output).
"""
from http.server import BaseHTTPRequestHandler
import json
import os
import time
import re
import urllib.request


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class handler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            data = json.loads(body) if body else {}
            email = (data.get("email") or "").strip().lower()
            source = (data.get("source") or "unknown").strip()[:50]
        except Exception as e:
            return self._send_json(400, {"error": f"Bad request: {e}"})

        if not EMAIL_RE.match(email):
            return self._send_json(400, {"error": "Invalid email"})

        record = {
            "email": email,
            "source": source,
            "ts": int(time.time()),
        }

        kv_url = os.environ.get("KV_REST_API_URL")
        kv_token = os.environ.get("KV_REST_API_TOKEN")
        stored = False
        if kv_url and kv_token:
            try:
                req = urllib.request.Request(
                    f"{kv_url}/lpush/khayaal_waitlist/{json.dumps(record)}",
                    headers={"Authorization": f"Bearer {kv_token}"},
                    method="POST",
                )
                urllib.request.urlopen(req, timeout=5).read()
                stored = True
            except Exception as e:
                print(f"[waitlist] KV store failed: {e}")

        # Always log to function output for visibility
        print(f"[waitlist] {json.dumps(record)} stored={stored}")
        return self._send_json(200, {"ok": True, "stored": stored})
