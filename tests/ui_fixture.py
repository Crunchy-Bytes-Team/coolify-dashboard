"""Explicitly synthetic UI fixture. Run with Python, then open localhost:3091.

Never connects to gateways or opens a production database.
"""
from pathlib import Path
import math
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from service import BoundedServer, make_handler


class Fixture:
    def route(self, path, query):
        now = int(time.time() * 1000)
        resource = {"id": "application:demo", "name": "Demo application", "project": "Example project",
                    "kind": "application", "running": 1, "cpu": 42.5, "memory": 512 * 1048576,
                    "cpu_at": now - 20000, "memory_at": now - 20000, "status": "fresh"}
        host = {**resource, "id": "server", "name": "Server", "kind": "server", "project": "",
                "memory_percent": 42.5, "memory_total": 8 * 1073741824, "memory": 3.4 * 1073741824}
        server = {"id": "demo", "name": "Example server", "enabled": True, "error": None,
                  "contacted": now - 10000, "metrics": host}
        if path == "/api/overview":
            return {"servers": [server], "poll_seconds": 30, "retention_days": 90, "now": now}
        if path == "/api/resources":
            return {"resources": [host, resource]}
        if path == "/api/projects":
            return {"projects": [{"name": "Example project", "resources": [
                {**resource, "server": "demo", "server_name": "Example server"}]}]}
        if path == "/api/alert-status":
            return {"checked_at": now, "targets": [{"key": "demo|server", "server": "demo",
                "entity": "server", "name": "Example server", "state": "normal"}]}
        metric = query.get("metric", ["cpu"])[0]
        hours = int(query.get("hours", ["24"])[0])
        step = hours * 3600000 // 60
        points = [{"time": now - (60-i)*step, "value": 40+10*math.sin(i/5),
                   "high": 55, "count": 1} for i in range(61)]
        if metric == "memory":
            for p in points:
                p["value"] *= 1073741824 / 12
                p["high"] *= 1073741824 / 12
        return {"metric": metric, "from": now-hours*3600000, "to": now,
                "bucket_ms": step, "samples": points}


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    app = BoundedServer(("127.0.0.1", 3091), make_handler("dashboard", Fixture(), web_root=root/"dist"))
    print("Synthetic UI fixture: http://localhost:3091", flush=True)
    app.serve_forever()
