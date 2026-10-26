"""ModDesk team sync server - self-hosted, standard library only (Python 3.8+).

  python moddesk-server.py --token YOUR_TEAM_KEY [--port 8787] [--dir ./moddesk-data]

In ModDesk (Settings > Team sync) use  http://<this-machine>:8787/<workspace-name>  and the same key.
One file per workspace is kept in --dir. Writes are locked, so two saves can never race.
Use HTTPS (a reverse proxy such as Caddy or nginx) if it is reachable outside your own network.
"""
import argparse
import json
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOCK = threading.Lock()


def make_handler(token, folder):
    class H(BaseHTTPRequestHandler):
        def reply(self, obj, status=200):
            body = json.dumps(obj).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def path_for(self):
            name = re.sub(r"[^A-Za-z0-9_.-]", "_", self.path.strip("/").split("?")[0]) or "default"
            return os.path.join(folder, name + ".json")

        def authed(self):
            if self.headers.get("Authorization", "") != "Bearer " + token:
                self.reply({"error": "unauthorized"}, 401)
                return False
            return True

        def load(self, path):
            try:
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, ValueError):
                return {"rev": 0, "data": None}

        def do_GET(self):
            if self.authed():
                with LOCK:
                    self.reply(self.load(self.path_for()))

        def do_PUT(self):
            if not self.authed():
                return
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            except ValueError:
                return self.reply({"error": "bad json"}, 400)
            path = self.path_for()
            with LOCK:
                cur = self.load(path)
                if body.get("base_rev") != cur["rev"]:
                    return self.reply(cur, 409)
                new = {"rev": cur["rev"] + 1, "data": body.get("data")}
                if os.path.exists(path):
                    os.replace(path, path + ".bak")
                with open(path + ".tmp", "w", encoding="utf-8") as f:
                    json.dump(new, f)
                os.replace(path + ".tmp", path)
            self.reply({"rev": new["rev"]})

        def log_message(self, *a):
            pass
    return H


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", required=True)
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--dir", default="moddesk-data")
    a = ap.parse_args()
    os.makedirs(a.dir, exist_ok=True)
    print("ModDesk sync server on port %d, data in %s" % (a.port, os.path.abspath(a.dir)))
    ThreadingHTTPServer(("0.0.0.0", a.port), make_handler(a.token, a.dir)).serve_forever()
