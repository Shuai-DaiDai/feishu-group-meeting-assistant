#!/usr/bin/env python3
import json
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

OUT_DIR = "/root/.openclaw/workspace/output"
os.makedirs(OUT_DIR, exist_ok=True)
LAST_JSON = os.path.join(OUT_DIR, "feishu-oauth-last.json")

HTML_OK = """<!doctype html><html><head><meta charset='utf-8'><title>OAuth OK</title></head>
<body><h2>Feishu OAuth 回调已接收 ✅</h2>
<p>你可以回到聊天窗口，告诉我“已授权”。</p>
</body></html>"""

class Handler(BaseHTTPRequestHandler):
    def _send(self, code=200, ctype="application/json", body="{}"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/health":
            return self._send(200, "application/json", json.dumps({"ok": True}))

        if u.path == "/feishu/oauth/callback":
            qs = parse_qs(u.query)
            payload = {
                "time": datetime.utcnow().isoformat() + "Z",
                "code": (qs.get("code") or [""])[0],
                "state": (qs.get("state") or [""])[0],
                "raw_query": u.query,
            }
            with open(LAST_JSON, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            return self._send(200, "text/html; charset=utf-8", HTML_OK)

        return self._send(404, "application/json", json.dumps({"error": "not_found"}))

if __name__ == "__main__":
    port = int(os.environ.get("FEISHU_OAUTH_PORT", "8787"))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"feishu oauth callback listening on :{port}")
    server.serve_forever()
