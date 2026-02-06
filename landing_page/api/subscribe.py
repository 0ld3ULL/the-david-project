#!/usr/bin/env python3
"""
Newsletter subscription API
Standard waitlist signup for product launch.
"""

import json
import os
import re
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
from collections import defaultdict

# Configuration
DATA_DIR = "/var/www/flipt/data"
SUBSCRIBERS_FILE = os.path.join(DATA_DIR, "waitlist.json")
RATE_LIMIT = 5  # requests per minute per IP

_rate_cache = defaultdict(list)

def _check_rate(ip):
    now = time.time()
    _rate_cache[ip] = [t for t in _rate_cache[ip] if now - t < 60]
    if len(_rate_cache[ip]) >= RATE_LIMIT:
        return False
    _rate_cache[ip].append(now)
    return True

def _valid_email(email):
    if not email or len(email) > 254:
        return None
    email = email.strip().lower()
    email = re.sub(r'<[^>]*>', '', email)
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return email if re.match(pattern, email) else None

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Quiet logging

    def _respond(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_OPTIONS(self):
        self._respond(200, {})

    def do_POST(self):
        if self.path != "/subscribe":
            return self._respond(404, {"error": "Not found"})

        # Get client IP
        ip = self.headers.get("X-Forwarded-For", "").split(",")[0].strip() or self.client_address[0]

        if not _check_rate(ip):
            return self._respond(429, {"error": "Please wait before trying again"})

        # Read body
        length = int(self.headers.get("Content-Length", 0))
        if length > 1024:
            return self._respond(413, {"error": "Request too large"})

        try:
            body = self.rfile.read(length).decode()
            data = json.loads(body) if "json" in self.headers.get("Content-Type", "") else dict(urllib.parse.parse_qsl(body))
        except:
            return self._respond(400, {"error": "Invalid request"})

        email = _valid_email(data.get("email", ""))
        if not email:
            return self._respond(400, {"error": "Invalid email"})

        # Load/save subscribers
        os.makedirs(DATA_DIR, exist_ok=True)
        subs = []
        if os.path.exists(SUBSCRIBERS_FILE):
            try:
                with open(SUBSCRIBERS_FILE) as f:
                    subs = json.load(f)
            except:
                pass

        if email in [s.get("email") for s in subs]:
            return self._respond(200, {"success": True, "message": "Already subscribed"})

        subs.append({
            "email": email,
            "date": datetime.utcnow().isoformat() + "Z"
        })

        with open(SUBSCRIBERS_FILE + ".tmp", "w") as f:
            json.dump(subs, f, indent=2)
        os.replace(SUBSCRIBERS_FILE + ".tmp", SUBSCRIBERS_FILE)

        return self._respond(200, {"success": True, "message": "Subscribed"})

if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 8082), Handler)
    print("Newsletter API running on :8082")
    server.serve_forever()
