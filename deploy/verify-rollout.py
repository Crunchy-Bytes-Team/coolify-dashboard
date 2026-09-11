"""Read-only gateway audit. Run inside the dashboard container with env files loaded."""
import concurrent.futures
import json
import os
import ssl
import time
import urllib.request
import urllib.error
from urllib.parse import urlencode

import service


def audit(row):
    result = {"id": row["id"], "name": row["name"]}
    token = os.environ[row["token_env"]]
    url = row["url"]
    try:
        inventory = service.fetch_json(url + "/v1/inventory", token, row.get("ca_file"))
        result["resources"] = len(inventory["resources"])
        result["tls_authenticated"] = True
        now = int(time.time() * 1000)
        for metric in ("cpu", "memory"):
            path = "/v1/history?" + urlencode({"container": "", "metric": metric,
                "from": service.iso(now - 300000), "to": service.iso(now)})
            data = service.fetch_json(url + path, token, row.get("ca_file"))
            result[metric + "_samples"] = len(data.get("samples", []))
        try:
            urllib.request.urlopen(url + "/v1/inventory", timeout=10,
                                   context=ssl.create_default_context(cafile=row.get("ca_file")))
            result["unauthenticated_status"] = 200
        except urllib.error.HTTPError as exc:
            result["unauthenticated_status"] = exc.code
    except Exception as exc:
        result["error"] = getattr(exc, "message", type(exc).__name__)
    return result


if __name__ == "__main__":
    import sys
    rows = json.load(sys.stdin)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for result in pool.map(audit, rows):
            print(json.dumps(result), flush=True)
