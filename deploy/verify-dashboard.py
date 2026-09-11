"""Read-only live collector verification, including independent refresh progress."""
import json
import time
import urllib.request
import service


def snapshot():
    started = time.monotonic()
    request = urllib.request.Request("http://dashboard:3090/api/overview", headers={"Host": "localhost:3090"})
    with urllib.request.urlopen(request, timeout=15) as response:
        overview = json.load(response)
    db = service.Database("/data/metrics.sqlite")
    applications = []
    for server in overview["servers"]:
        applications.extend({"server": server["name"], "name": row["name"],
            "status": row["status"], "running": row["running"]}
            for row in db.entities(server["id"]) if row["kind"] == "application")
    return {"at": int(time.time()*1000), "overview_ms": round((time.monotonic()-started)*1000),
        "hosts": [{"id": row["id"], "name": row["name"], "error": row["error"],
            "status": (row["metrics"] or {}).get("status"),
            "cpu_at": (row["metrics"] or {}).get("cpu_at"),
            "memory_at": (row["metrics"] or {}).get("memory_at")}
            for row in overview["servers"]],
        "applications": len(applications),
        "applications_fresh": sum(row["status"] == "fresh" for row in applications),
        "applications_without_fresh_data": [row for row in applications if row["status"] != "fresh"]}


if __name__ == "__main__":
    first = snapshot()
    print(json.dumps({"first_snapshot": first}), flush=True)
    time.sleep(40)
    second = snapshot()
    previous = {row["id"]: row for row in first["hosts"]}
    advanced = [row["name"] for row in second["hosts"]
        if all((row[metric + "_at"] or 0) > (previous[row["id"]][metric + "_at"] or 0)
               for metric in ("cpu", "memory"))]
    print(json.dumps({"final_snapshot": second, "both_metrics_advanced": advanced}), flush=True)
