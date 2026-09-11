"""Read-only threshold evaluation against actual samples, including gaps and replicas."""
import math
import time


def sustained(points, threshold, duration, now):
    if not points or now-points[-1][0] > 60000:
        return {"state":"unknown"}
    latest = points[-1]
    if latest[1] <= threshold:
        return {"state":"normal","value":latest[1]}
    start = latest[0]
    for timestamp, value in reversed(points[:-1]):
        if start-timestamp > 15000 or value <= threshold:
            break
        start = timestamp
    return {"state":"active" if latest[0]-start >= duration*1000 else "pending",
            "value":latest[1],"since":start}


def evaluate(config, database, query, now=None):
    from service import Problem, one
    now = now if now is not None else int(time.time()*1000)
    server = one(query,"server","*")
    entity = one(query,"entity","server")
    if len(entity)>400 or (server=="*" and entity!="server"):
        raise Problem(400,"Destinazione allarme non valida.")
    try:
        duration = int(one(query,"seconds","30"))
        cpu = float(one(query,"cpu","80"))
        memory = float(one(query,"memory","80"))
        if not 10<=duration<=1800 or not all(math.isfinite(v) and v>0 for v in (cpu,memory)):
            raise ValueError()
        if cpu>10000 or memory>(100 if entity=="server" else 10485760):
            raise ValueError()
    except (TypeError,ValueError):
        raise Problem(400,"Soglie o durata non valide.") from None
    selected = [s for s in config["servers"] if s["enabled"] and server in ("*",s["id"])]
    if not selected:
        raise Problem(404,"Server non trovato.")
    targets = []
    for node in selected:
        with database.connect() as db:
            sources = db.execute("SELECT source,name FROM sources WHERE server=? AND entity=? AND state='running'",
                                 (node["id"],entity)).fetchall()
            health = db.execute("SELECT error FROM status WHERE server=?",(node["id"],)).fetchone()
            metrics = {}
            for metric, threshold in (("cpu",cpu),("memory_percent" if entity=="server" else "memory",memory if entity=="server" else memory*1048576)):
                per_source = []
                raw_points = []
                for source in sources:
                    rows = db.execute("SELECT ts,value FROM samples WHERE server=? AND source=? AND metric=? AND ts>=? AND ts<=? ORDER BY ts",
                        (node["id"],source["source"],metric,now-(duration+90)*1000,now)).fetchall()
                    raw_points = [(row["ts"],row["value"]) for row in rows]
                    buckets = {}
                    for row in rows:
                        tick = row["ts"]//10000*10000
                        buckets[tick] = min(buckets.get(tick,row["value"]),row["value"])
                    per_source.append(buckets)
                # Only complete replica sets count as evidence of a sustained total.
                ticks = sorted(set.intersection(*(set(p) for p in per_source))) if per_source else []
                points = raw_points if len(per_source)==1 else [(tick,sum(p[tick] for p in per_source)) for tick in ticks]
                # With replicas, reserve one bucket to avoid counting unobserved time at its edges.
                required = duration if len(per_source)==1 else duration+10
                metrics["memory" if metric.startswith("memory") else metric] = sustained(points,threshold,required,now)
            states = [m["state"] for m in metrics.values()]
            state = "unknown" if not sources or (health and health["error"]) else "active" if "active" in states else "unknown" if "unknown" in states else "pending" if "pending" in states else "normal"
            targets.append({"key":node["id"]+"|"+entity,"server":node["id"],"entity":entity,
                "name":node["name"] if entity=="server" else node["name"]+" / "+(sources[0]["name"] if sources else entity),
                "state":state,"metrics":metrics,"memory_unit":"%" if entity=="server" else "bytes"})
    return {"checked_at":now,"targets":targets}
