"""Local Sentinel dashboard, restricted HTTPS gateway and host-side reader.

Python standard library only. No SSH, shell execution or Docker write operations.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import concurrent.futures
import hmac
import http.client
import ipaddress
import json
import logging
import math
import os
from pathlib import Path
import re
import signal
import socket
import socketserver
import sqlite3
import ssl
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener

LOG = logging.getLogger("sentinel-dashboard")
MAX_BODY = 8 * 1024 * 1024
UTC = timezone.utc
NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,199}$")
METRICS = ("cpu", "memory")
STOP = threading.Event()


class Problem(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message
        super().__init__(message)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Problem(502, "Il servizio ha restituito un redirect inatteso.")


def secret(name):
    filename = os.getenv(name + "_FILE")
    value = Path(filename).read_text().strip() if filename else os.getenv(name, "").strip()
    if len(value) < 32:
        raise ValueError(name + " deve contenere almeno 32 caratteri.")
    return value


def fetch_json(url, token=None, ca_file=None):
    context = ssl.create_default_context(cafile=ca_file)
    # Do not pass infrastructure credentials through ambient HTTP proxies.
    opener = build_opener(ProxyHandler({}), HTTPSHandler(context=context), NoRedirect())
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        with opener.open(Request(url, headers=headers), timeout=12) as response:
            payload = response.read(MAX_BODY + 1)
            if len(payload) > MAX_BODY:
                raise Problem(502, "Risposta troppo grande: ridurre l'intervallo.")
            return json.loads(payload)
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise Problem(502, "Autenticazione del servizio non riuscita.") from None
        raise Problem(502, "Il servizio metriche non ha risposto correttamente.") from None
    except (URLError, TimeoutError, OSError, ValueError):
        raise Problem(502, "Servizio non raggiungibile o risposta non valida.") from None


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def timestamp(value):
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
        result = int(value)
    else:
        date = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if date.tzinfo is None:
            raise ValueError("Timezone required")
        result = int(date.timestamp() * 1000)
    if not 0 <= result <= 4102444800000:
        raise ValueError("Invalid timestamp")
    return result


def one(query, key, default=None):
    values = query.get(key, [default])
    if len(values) != 1:
        raise Problem(400, "Parametro duplicato.")
    return values[0]


def history_query(query):
    if set(query) - {"container", "metric", "from", "to"}:
        raise Problem(400, "Parametro non consentito.")
    metric = one(query, "metric")
    container = one(query, "container", "")
    if metric not in METRICS or (container and not NAME.fullmatch(container)):
        raise Problem(400, "Risorsa o metrica non valida.")
    try:
        start, end = timestamp(one(query, "from")), timestamp(one(query, "to"))
        if not 0 < end - start <= 6 * 3600_000:
            raise ValueError()
        if end > int(time.time() * 1000) + 60_000:
            raise ValueError()
    except (TypeError, ValueError, OverflowError):
        raise Problem(400, "Intervallo UTC non valido; massimo 6 ore.") from None
    return container, metric, start, end


class DockerConnection(http.client.HTTPConnection):
    def __init__(self):
        super().__init__("localhost", timeout=8)

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(os.getenv("DOCKER_SOCKET", "/var/run/docker.sock"))


def docker_read(path):
    # This function intentionally accepts only these two exact Docker endpoints.
    if path not in ("/containers/json?all=true", "/containers/coolify-sentinel/json"):
        raise Problem(403, "Operazione Docker non consentita.")
    connection = DockerConnection()
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        payload = response.read(MAX_BODY + 1)
        if response.status != 200 or len(payload) > MAX_BODY:
            raise Problem(502, "Sentinel o inventario Docker non disponibili.")
        return json.loads(payload)
    except (OSError, ValueError, http.client.HTTPException):
        raise Problem(502, "Inventario Docker non raggiungibile.") from None
    finally:
        connection.close()


def identify(item):
    labels = item.get("Labels") or {}
    names = item.get("Names") or []
    # Sentinel keys its histories on coolify.name, which omits deploy suffixes.
    name = labels.get("coolify.name") or (names[0].lstrip("/") if names else str(item.get("Id", ""))[:12])
    if not NAME.fullmatch(name):
        return None
    app = labels.get("coolify.applicationId")
    service = labels.get("coolify.serviceId")
    database = labels.get("coolify.databaseId")
    if app:
        resource_id, kind = "application:" + str(app), "application"
    elif database:
        resource_id, kind = "database:" + str(database), "database"
    elif service:
        # Do not silently sum a service's database, proxy and application.
        sub = labels.get("coolify.service.subId") or labels.get("com.docker.compose.service") or name
        resource_id, kind = "service:" + str(service) + ":" + str(sub), "service"
    else:
        resource_id, kind = "container:" + name, "container"
    display = labels.get("coolify.resourceName") or labels.get("coolify.name") or name
    if service:
        display = labels.get("coolify.service.subName") or labels.get("coolify.serviceName") or display
    return {"source": name, "id": resource_id, "name": str(display)[:200], "kind": kind,
            "project": str(labels.get("coolify.projectName", ""))[:200],
            "state": item.get("State", "unknown"), "created": item.get("Created")}


class Reader:
    def __init__(self):
        self.cached = None
        self.cache_time = 0
        self.lock = threading.Lock()

    def upstream(self):
        with self.lock:
            if self.cached and time.monotonic() - self.cache_time < 10:
                return self.cached
            item = docker_read("/containers/coolify-sentinel/json")
            networks = item.get("NetworkSettings", {})
            bridge = networks.get("Networks", {}).get("bridge", {})
            address = bridge.get("IPAddress") or networks.get("IPAddress")
            try:
                parsed = ipaddress.ip_address(address)
                if parsed.version != 4 or not parsed.is_private or parsed.is_unspecified:
                    raise ValueError()
            except (TypeError, ValueError):
                raise Problem(503, "Rete Sentinel non supportata: verificare la configurazione del pilota.") from None
            env = item.get("Config", {}).get("Env") or []
            token = next((v.partition("=")[2] for v in env if v.startswith("TOKEN=")), "")
            if not token:
                raise Problem(503, "Token Sentinel non disponibile.")
            self.cached = ("http://" + address + ":8888", token)
            self.cache_time = time.monotonic()
            return self.cached

    def history(self, query):
        container, metric, start, end = history_query(query)
        base, token = self.upstream()
        path = "/api/" + metric + "/history"
        if container:
            path = "/api/container/" + quote(container, safe="") + "/" + metric + "/history"
        try:
            rows = fetch_json(base + path + "?" + urlencode({"from": iso(start), "to": iso(end)}), token)
        except Problem:
            self.cache_time = 0
            raise
        if rows is None:
            rows = []
        if not isinstance(rows, list):
            raise Problem(502, "Formato Sentinel non riconosciuto.")
        output = []
        for row in rows:
            try:
                ts = timestamp(row["time"])
                value = float(row["percent"] if metric == "cpu" else row["used"])
                if start <= ts <= end and math.isfinite(value) and value >= 0:
                    sample = {"time": ts, "value": value}
                    if metric == "memory" and not container:
                        try:
                            total = float(row["total"])
                            if math.isfinite(total) and total > 0 and value <= total:
                                sample["total"] = total
                        except (KeyError, TypeError, ValueError, OverflowError):
                            pass
                    output.append(sample)
            except (KeyError, TypeError, ValueError, OverflowError):
                continue
        # Reject a changed schema rather than quietly advancing the collection cursor.
        if rows and not output:
            raise Problem(502, "Nessun campione Sentinel valido nell'intervallo.")
        return {"metric": metric, "container": container, "unit": "%" if metric == "cpu" else "bytes",
                "samples": output}

    def inventory(self):
        self.upstream()  # Rediscover after every cache expiry, including Sentinel replacement.
        items = docker_read("/containers/json?all=true")
        resources = [r for item in items if (r := identify(item))]
        return {"resources": resources, "observed_at": int(time.time() * 1000)}


class ReaderConnection(http.client.HTTPConnection):
    def __init__(self):
        super().__init__("localhost", timeout=12)

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(os.getenv("READER_SOCKET", "/run/metrics/reader.sock"))


def reader_json(path, token=None):
    if urlsplit(path).path not in ("/health", "/v1/inventory", "/v1/history"):
        raise Problem(403, "Endpoint del lettore non consentito.")
    connection = ReaderConnection()
    try:
        headers = {"Authorization": "Bearer " + token} if token else {}
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        payload = response.read(MAX_BODY + 1)
        if response.status != 200 or len(payload) > MAX_BODY:
            raise Problem(502, "Il lettore interno non ha risposto correttamente.")
        return json.loads(payload)
    except (OSError, ValueError, http.client.HTTPException):
        raise Problem(502, "Socket del lettore non raggiungibile o risposta non valida.") from None
    finally:
        connection.close()


class Gateway:
    def __init__(self):
        self.token = secret("READER_TOKEN")

    def inventory(self):
        return reader_json("/v1/inventory", self.token)

    def history(self, query):
        container, metric, start, end = history_query(query)
        return reader_json("/v1/history?" + urlencode(
            {"container": container, "metric": metric, "from": iso(start), "to": iso(end)}), self.token)


SCHEMA = """
CREATE TABLE IF NOT EXISTS sources(
 server TEXT, source TEXT, entity TEXT, name TEXT, kind TEXT, project TEXT,
 state TEXT, seen INTEGER, PRIMARY KEY(server,source));
CREATE TABLE IF NOT EXISTS samples(
 server TEXT, source TEXT, metric TEXT, ts INTEGER, value REAL,
 PRIMARY KEY(server,source,metric,ts)) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS samples_time ON samples(server,metric,ts);
CREATE INDEX IF NOT EXISTS samples_retention ON samples(ts);
CREATE INDEX IF NOT EXISTS source_entity ON sources(server,entity,source);
CREATE TABLE IF NOT EXISTS rollups(
 server TEXT, entity TEXT, metric TEXT, ts INTEGER, value REAL, low REAL, high REAL, count INTEGER,
 PRIMARY KEY(server,entity,metric,ts)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS cursors(
 server TEXT, source TEXT, metric TEXT, until INTEGER, backfill INTEGER,
 error TEXT, PRIMARY KEY(server,source,metric));
CREATE TABLE IF NOT EXISTS status(
 server TEXT PRIMARY KEY, contacted INTEGER, error TEXT);
CREATE TABLE IF NOT EXISTS memory_capacity(
 server TEXT PRIMARY KEY, ts INTEGER, total REAL);
"""


class Database:
    def __init__(self, path):
        self.path = str(path)
        self.write_condition = threading.Condition()
        self.write_ticket = 0
        self.write_turn = 0
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript(SCHEMA)

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=20)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=20000")
        # Samples can be recovered from Sentinel after a power loss. WAL/NORMAL
        # keeps the database consistent without an fsync for every tiny poll write.
        connection.execute("PRAGMA synchronous=NORMAL")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @contextmanager
    def write(self):
        # SQLite has one writer. Queue local collectors before opening transactions,
        # leaving WAL readers independent instead of timing out competing writers.
        with self.write_condition:
            ticket = self.write_ticket
            self.write_ticket += 1
            self.write_condition.wait_for(lambda: ticket == self.write_turn)
        try:
            with self.connect() as connection:
                yield connection
        finally:
            with self.write_condition:
                self.write_turn += 1
                self.write_condition.notify_all()

    def inventory(self, server, resources, now):
        with self.write() as db:
            db.execute("UPDATE sources SET state='missing' WHERE server=? AND source!=''", (server,))
            rows = [{"source": "", "id": "server", "name": "Server", "kind": "server", "project": "", "state": "running"}] + resources
            for row in rows:
                db.execute("INSERT INTO sources VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(server,source) DO UPDATE SET entity=excluded.entity,name=excluded.name,kind=excluded.kind,project=excluded.project,state=excluded.state,seen=excluded.seen",
                           (server, row["source"], row["id"], row["name"], row["kind"], row["project"], row["state"], now))

    def ingest(self, server, source, metric, samples, start, end, historical=False):
        valid = []
        capacities = []
        percentages = []
        for sample in samples:
            ts, value = timestamp(sample["time"]), float(sample["value"])
            if not (start <= ts <= end and math.isfinite(value) and value >= 0):
                raise ValueError("Campione non valido.")
            valid.append((server, source, metric, ts, value))
            if source == "" and metric == "memory":
                try:
                    total = float(sample["total"])
                    if math.isfinite(total) and total > 0 and value <= total:
                        capacities.append((server,ts,total))
                        if ts >= int(time.time()*1000)-40*60_000:
                            percentages.append((server,source,"memory_percent",ts,value/total*100))
                except (KeyError, TypeError, ValueError, OverflowError):
                    pass
        with self.write() as db:
            db.executemany("INSERT OR REPLACE INTO samples VALUES(?,?,?,?,?)", valid)
            db.executemany("INSERT OR REPLACE INTO samples VALUES(?,?,?,?,?)", percentages)
            db.executemany("""INSERT INTO memory_capacity VALUES(?,?,?) ON CONFLICT(server)
                DO UPDATE SET ts=excluded.ts,total=excluded.total WHERE excluded.ts>=memory_capacity.ts""", capacities)
            if historical:
                db.execute("UPDATE cursors SET backfill=?,error=NULL WHERE server=? AND source=? AND metric=?",
                           (start, server, source, metric))
            else:
                db.execute("INSERT INTO cursors VALUES(?,?,?,?,?,NULL) ON CONFLICT(server,source,metric) DO UPDATE SET until=MAX(COALESCE(until,0),excluded.until),backfill=COALESCE(backfill,excluded.backfill),error=NULL",
                           (server, source, metric, end, start))

    def cursor(self, server, source, metric):
        with self.connect() as db:
            row = db.execute("SELECT * FROM cursors WHERE server=? AND source=? AND metric=?", (server, source, metric)).fetchone()
            return dict(row) if row else None

    def set_error(self, server, error=None, source=None, metric=None):
        with self.write() as db:
            if source is None:
                if error:
                    db.execute("INSERT INTO status VALUES(?,NULL,?) ON CONFLICT(server) DO UPDATE SET error=excluded.error", (server, error))
                else:
                    db.execute("INSERT INTO status VALUES(?,?,NULL) ON CONFLICT(server) DO UPDATE SET contacted=excluded.contacted,error=NULL", (server, int(time.time()*1000)))
            else:
                db.execute("INSERT INTO cursors VALUES(?,?,?,NULL,NULL,?) ON CONFLICT(server,source,metric) DO UPDATE SET error=excluded.error", (server, source, metric, error))

    def entities(self, server, entity=None):
        with self.connect() as db:
            rows = db.execute("""SELECT entity AS id, MAX(name) AS name, MAX(kind) AS kind,
                MAX(project) AS project, SUM(state='running') AS running, COUNT(*) AS containers
                FROM sources WHERE server=? AND (? IS NULL OR entity=?)
                GROUP BY entity ORDER BY kind,name""", (server,entity,entity)).fetchall()
            output = []
            now = int(time.time()*1000)
            for row in rows:
                item = dict(row)
                for metric in METRICS:
                    latest = db.execute("""SELECT MAX((SELECT m.ts FROM samples m
                      WHERE m.server=s.server AND m.source=s.source AND m.metric=?
                      ORDER BY m.ts DESC LIMIT 1)) FROM sources s WHERE s.server=? AND s.entity=?""",
                      (metric,server,item["id"])).fetchone()[0]
                    item[metric + "_at"] = latest
                    if latest is not None:
                        # Last values from sources actually sampled near this entity's last time.
                        value = db.execute("""SELECT SUM(value) FROM (
                          SELECT m.source, m.value, ROW_NUMBER() OVER(PARTITION BY m.source ORDER BY m.ts DESC) AS rn
                          FROM samples m JOIN sources s ON m.server=s.server AND m.source=s.source
                          WHERE m.server=? AND s.entity=? AND m.metric=? AND m.ts>=?) WHERE rn=1""",
                          (server, item["id"], metric, latest - 20_000)).fetchone()[0]
                        item[metric] = value
                    else:
                        item[metric] = None
                last = min((item[m + "_at"] or 0 for m in METRICS), default=0)
                errors = db.execute("""SELECT COUNT(*) FROM cursors c JOIN sources s
                  ON c.server=s.server AND c.source=s.source WHERE c.server=? AND s.entity=? AND c.error IS NOT NULL""",
                  (server, item["id"])).fetchone()[0]
                item["status"] = "error" if errors else "waiting" if not last else "fresh" if now-last<120_000 else "stale"
                if item["status"] == "fresh" and item["running"] > 1:
                    incomplete = db.execute("""SELECT COUNT(*) FROM sources s WHERE s.server=? AND s.entity=?
                      AND s.state='running' AND (SELECT COUNT(DISTINCT metric) FROM samples m
                      WHERE m.server=s.server AND m.source=s.source AND m.ts>?)<2""",
                      (server,item["id"],now-120_000)).fetchone()[0]
                    if incomplete:
                        item["status"] = "partial"
                if item["id"] == "server":
                    capacity = db.execute("SELECT ts,total FROM memory_capacity WHERE server=?", (server,)).fetchone()
                    total = capacity["total"] if capacity and capacity["ts"] == item["memory_at"] else None
                    item["memory_total"] = total
                    item["memory_percent"] = item["memory"] / total * 100 if total and item["memory"] is not None else None
                output.append(item)
            return output

    def series(self, server, entity, metric, start, end):
        bucket = max(10_000, math.ceil((end-start)/300/10_000)*10_000)
        if end-start >= 7*86400_000:
            bucket = max(300_000, math.ceil(bucket/300_000)*300_000)
        with self.connect() as db:
            rows = db.execute("""WITH per_source AS (
              SELECT (m.ts/10000)*10000 AS tick,m.source,AVG(m.value) AS value
              FROM samples m JOIN sources s ON m.server=s.server AND m.source=s.source
              WHERE m.server=? AND s.entity=? AND m.metric=? AND m.ts>=? AND m.ts<=?
              GROUP BY tick,m.source), per_tick AS (
              SELECT tick,SUM(value) AS value FROM per_source GROUP BY tick)
              , combined AS (
              SELECT tick,value,value AS low,value AS high,1 AS count FROM per_tick
              UNION ALL SELECT ts,value,low,high,count FROM rollups
              WHERE server=? AND entity=? AND metric=? AND ts>=? AND ts<=?)
              SELECT (tick/?)*? AS time,SUM(value*count)/SUM(count) AS value,
              MIN(low) AS low,MAX(high) AS high,SUM(count) AS count
              FROM combined GROUP BY time ORDER BY time""",
              (server, entity, metric, start, end, server,entity,metric,start,end,bucket,bucket)).fetchall()
        return {"metric": metric, "unit": "%" if metric=="cpu" else "bytes", "bucket_ms": bucket,
                "from": start, "to": end, "samples": [dict(row) for row in rows]}

    def compact(self, retention_days, now=None):
        now = now or int(time.time()*1000)
        cutoff = ((now - 7*86400_000)//300_000)*300_000
        with self.write() as db:
            db.execute("""INSERT OR REPLACE INTO rollups
              WITH per_source AS (
                SELECT m.server,s.entity,m.metric,m.source,(m.ts/10000)*10000 AS tick,AVG(m.value) AS value
                FROM samples m JOIN sources s ON m.server=s.server AND m.source=s.source
                WHERE m.ts<? GROUP BY m.server,s.entity,m.metric,m.source,tick),
              per_tick AS (SELECT server,entity,metric,tick,SUM(value) AS value
                FROM per_source GROUP BY server,entity,metric,tick)
              SELECT server,entity,metric,(tick/300000)*300000,AVG(value),MIN(value),MAX(value),COUNT(*)
              FROM per_tick GROUP BY server,entity,metric,(tick/300000)""",(cutoff,))
            db.execute("DELETE FROM samples WHERE ts<?",(cutoff,))
            db.execute("DELETE FROM rollups WHERE ts<?",(now-retention_days*86400_000,))


def load_config(path):
    config = json.loads(Path(path).read_text())
    if not isinstance(config.get("servers"), list):
        raise ValueError("servers deve essere una lista.")
    ids = set()
    for server in config["servers"]:
        if not NAME.fullmatch(server["id"]) or server["id"] in ids:
            raise ValueError("ID server non valido o duplicato.")
        ids.add(server["id"])
        server.setdefault("enabled", False)
        server["sentinel_retention_days"] = min(7,max(1,int(server.get("sentinel_retention_days",7))))
        if server["enabled"]:
            url = urlsplit(server["url"])
            if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in ("", "/"):
                raise ValueError("Ogni gateway deve avere un URL HTTPS senza credenziali o percorso.")
            if server.get("token_env"):
                server["token"] = os.environ.get(server["token_env"], "").strip()
            else:
                server["token"] = Path(server["token_file"]).read_text().strip()
            if len(server["token"]) < 32:
                raise ValueError("Token gateway mancante o troppo corto.")
    config["poll_seconds"] = max(15, int(config.get("poll_seconds", 30)))
    config["retention_days"] = min(365, max(7, int(config.get("retention_days", 90))))
    return config


class Collector:
    def __init__(self, config, db, request=fetch_json):
        self.config, self.db, self.request = config, db, request

    def get(self, server, path):
        return self.request(server["url"].rstrip("/") + path, server["token"], server.get("ca_file"))

    def collect_metric(self, server, source, metric, historical=False):
        now = int(time.time())*1000
        key = server["id"]
        cursor = self.db.cursor(key, source, metric)
        floor = now - min(self.config["retention_days"], int(server.get("sentinel_retention_days",7))) * 86400_000
        if historical:
            if not cursor or not cursor["backfill"] or cursor["backfill"] <= floor:
                return
            end = cursor["backfill"]
            start = max(floor, end - 3600_000)
        else:
            start = max(floor, (cursor["until"] - 60_000) if cursor and cursor["until"] else now-15*60_000)
            end = min(now, start+6*3600_000)
        try:
            payload = self.get(server, "/v1/history?" + urlencode({"container":source,"metric":metric,"from":iso(start),"to":iso(end)}))
            if payload.get("metric") != metric or payload.get("container") != source or not isinstance(payload.get("samples"),list):
                raise ValueError()
            self.db.ingest(key,source,metric,payload["samples"],start,end,historical)
        except (Problem, ValueError, KeyError, TypeError) as exc:
            self.db.set_error(key, exc.message if isinstance(exc,Problem) else "Formato dei campioni non valido.",source,metric)

    def collect_servers(self, servers, include_history=True):
        for server in servers:
            if STOP.is_set():
                return
            if not server["enabled"]:
                continue
            key = server["id"]
            try:
                payload = self.get(server, "/v1/inventory")
                resources = payload["resources"]
                if not isinstance(resources, list) or len(resources)>2000:
                    raise ValueError()
                for resource in resources:
                    if not NAME.fullmatch(resource["source"]):
                        raise ValueError()
                    for field in ("id","name","kind","project","state"):
                        if not isinstance(resource[field],str) or len(resource[field])>400:
                            raise ValueError()
                self.db.inventory(key, resources, int(time.time()*1000))
                self.db.set_error(key)
                with self.db.connect() as db:
                    # Keep querying previously discovered names through redeploys within retention.
                    sources = [row[0] for row in db.execute("SELECT source FROM sources WHERE server=? AND (state='running' OR seen>?)",
                      (key,int(time.time()*1000)-int(server.get("sentinel_retention_days",7))*86400_000))]
                jobs = [(source,metric) for source in sources for metric in METRICS]
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                    list(pool.map(lambda task: self.collect_metric(server,*task),jobs))
                if include_history:
                    self.collect_backfill(server)
            except (Problem, ValueError, KeyError, TypeError) as exc:
                self.db.set_error(key,exc.message if isinstance(exc,Problem) else "Inventario non valido.")

    def collect_backfill(self, server):
        if STOP.is_set():
            return
        with self.db.connect() as db:
            backlog = db.execute("""SELECT source,metric FROM cursors WHERE server=? AND backfill>?
              ORDER BY backfill DESC LIMIT 4""", (server["id"],int(time.time()*1000)-min(int(server.get("sentinel_retention_days",7)),self.config["retention_days"])*86400_000)).fetchall()
        for row in backlog:
            if not STOP.is_set():
                self.collect_metric(server,row["source"],row["metric"],True)

    def cycle(self):
        # Bound aggregate load while keeping slow hosts independent of other hosts.
        servers = [server for server in self.config["servers"] if server["enabled"]]
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda server: self.collect_servers([server]), servers))
        self.db.compact(self.config["retention_days"])

    def run(self):
        servers = [server for server in self.config["servers"] if server["enabled"]]

        def live_loop(server):
            while not STOP.is_set():
                started = time.monotonic()
                try:
                    self.collect_servers([server], include_history=False)
                except Exception as exc:
                    # Never log response bodies, URLs, Docker environments or credentials.
                    LOG.error("Raccolta corrente interrotta (%s %s); nuovo tentativo automatico.",type(exc).__name__,getattr(exc,"sqlite_errorname",""))
                STOP.wait(max(0.1,self.config["poll_seconds"]-(time.monotonic()-started)))

        # Each host has its own polling clock. Historical downloads cannot hold it up.
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1,len(servers))) as live_pool:
            for server in servers:
                live_pool.submit(live_loop,server)
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as history_pool:
                while not STOP.is_set():
                    try:
                        list(history_pool.map(self.collect_backfill,servers))
                        if not STOP.is_set():
                            self.db.compact(self.config["retention_days"])
                    except Exception:
                        LOG.error("Recupero storico interrotto; nuovo tentativo automatico.")
                    STOP.wait(60)


class Dashboard:
    def __init__(self, config, db):
        self.config, self.db = config, db

    def overview(self):
        servers = []
        with self.db.connect() as db:
            for server in self.config["servers"]:
                row = db.execute("SELECT contacted,error FROM status WHERE server=?",(server["id"],)).fetchone()
                entities = self.db.entities(server["id"], "server")
                resource_count = db.execute("SELECT COUNT(DISTINCT entity) FROM sources WHERE server=? AND entity!='server'",
                  (server["id"],)).fetchone()[0]
                metric_server = next((e for e in entities if e["id"]=="server"),None)
                servers.append({"id":server["id"],"name":server["name"],"enabled":server["enabled"],
                  "contacted":row["contacted"] if row else None,"error":row["error"] if row else None,
                  "metrics":metric_server,"resources":resource_count})
        return {"servers":servers,"poll_seconds":self.config["poll_seconds"],"retention_days":self.config["retention_days"],
                "now":int(time.time()*1000)}

    def route(self, path, query):
        if path == "/api/overview":
            return self.overview()
        if path == "/api/projects":
            projects = {}
            with self.db.connect() as db:
                for node in self.config["servers"]:
                    if not node["enabled"]:
                        continue
                    rows = db.execute("""SELECT entity,project,MAX(name) AS name FROM sources
                        WHERE server=? AND project!='' AND state!='missing'
                        GROUP BY entity,project ORDER BY project,name""",(node["id"],)).fetchall()
                    for row in rows:
                        projects.setdefault(row["project"],[]).append({"server":node["id"],"server_name":node["name"],
                            "id":row["entity"],"name":row["name"]})
            return {"projects":[{"name":name,"resources":rows} for name,rows in sorted(projects.items())]}
        if path == "/api/alert-status":
            from alerts import evaluate
            return evaluate(self.config,self.db,query)
        server = one(query,"server")
        if server not in {s["id"] for s in self.config["servers"]}:
            raise Problem(404,"Server non trovato.")
        if path == "/api/resources":
            return {"resources":self.db.entities(server)}
        if path == "/api/history":
            metric = one(query,"metric")
            try:
                hours = int(one(query,"hours","24"))
            except (TypeError,ValueError):
                raise Problem(400,"Intervallo non valido.") from None
            if metric not in METRICS or hours not in (1,6,24,168,720,2160):
                raise Problem(400,"Intervallo o metrica non validi.")
            entity = one(query,"entity","server")
            if len(entity)>400:
                raise Problem(400,"Risorsa non valida.")
            now = int(time.time()*1000)
            return self.db.series(server,entity,metric,now-hours*3600_000,now)
        raise Problem(404,"Pagina non trovata.")


class BoundedServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 16

    def __init__(self, address, handler):
        self.slots = threading.BoundedSemaphore(16)
        super().__init__(address, handler)

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            request.close()
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


class UnixBoundedServer(BoundedServer):
    address_family = socket.AF_UNIX

    def __init__(self, path, handler):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_socket():
            target.unlink()
        super().__init__(str(target), handler)
        # Reader runs with group 10001; only the gateway shares that group and volume.
        target.chmod(0o660)

    def server_bind(self):
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = "localhost", 0


def make_handler(role, app, token=None, web_root=None):
    class Handler(BaseHTTPRequestHandler):
        server_version = "Metrics"
        sys_version = ""

        def setup(self):
            super().setup()
            self.connection.settimeout(15)

        def log_message(self, format, *args):
            pass

        def reply(self, status, payload, content_type="application/json; charset=utf-8"):
            data = payload if isinstance(payload,bytes) else json.dumps(payload,allow_nan=False).encode()
            self.send_response(status)
            self.send_header("Content-Type",content_type)
            self.send_header("Content-Length",str(len(data)))
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("Content-Security-Policy","default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.send_header("Referrer-Policy","no-referrer")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            try:
                parts = urlsplit(self.path)
                if parts.scheme or parts.netloc:
                    raise Problem(400,"Percorso non valido.")
                if role=="dashboard":
                    host = self.headers.get("Host","").split(":")[0].lower()
                    allowed_hosts = {"localhost", "127.0.0.1"}
                    allowed_hosts.update(x.strip().lower() for x in os.getenv("DASHBOARD_ALLOWED_HOSTS","").split(",") if x.strip())
                    if host not in allowed_hosts:
                        raise Problem(403,"Indirizzo della dashboard non autorizzato.")
                if parts.path=="/health":
                    return self.reply(200,{"status":"ok","role":role})
                if role!="dashboard":
                    expected = "Bearer " + token
                    if not hmac.compare_digest(self.headers.get("Authorization","").encode(),expected.encode()):
                        return self.reply(401,{"error":"Autenticazione richiesta."})
                    if parts.path not in ("/v1/inventory","/v1/history"):
                        raise Problem(404,"Endpoint non disponibile.")
                    query = parse_qs(parts.query,keep_blank_values=True,max_num_fields=8,strict_parsing=True)
                    if parts.path=="/v1/inventory" and query:
                        raise Problem(400,"Parametro non consentito.")
                    result = app.inventory() if parts.path=="/v1/inventory" else app.history(query)
                elif parts.path.startswith("/api/"):
                    result = app.route(parts.path,parse_qs(parts.query,keep_blank_values=True,max_num_fields=8))
                else:
                    assets = {"/":("index.html","text/html; charset=utf-8"),
                              "/app.js":("app.js","text/javascript; charset=utf-8"),
                              "/styles.css":("styles.css","text/css; charset=utf-8"),
                              "/favicon.svg":("favicon.svg","image/svg+xml"),
                              "/setup/gateway.yaml":("../gateway.yaml","text/plain; charset=utf-8")}
                    if parts.path not in assets:
                        raise Problem(404,"Pagina non trovata.")
                    filename, content_type = assets[parts.path]
                    return self.reply(200,(Path(web_root)/filename).read_bytes(),content_type)
                self.reply(200,result)
            except Problem as exc:
                self.reply(exc.status,{"error":exc.message})
            except (ValueError,TypeError):
                self.reply(400,{"error":"Richiesta non valida."})
            except (BrokenPipeError,ConnectionResetError):
                pass
            except Exception:
                LOG.error("Richiesta fallita; dettagli sensibili omessi.")
                self.reply(500,{"error":"Errore interno del servizio."})

        def do_POST(self):
            self.reply(405,{"error":"Sono consentite soltanto richieste GET."})

        do_PUT = do_POST
        do_PATCH = do_POST
        do_DELETE = do_POST
        do_OPTIONS = do_POST
    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("role",choices=("dashboard","gateway","reader"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO,format="%(levelname)s %(message)s")
    role = args.role
    if role=="dashboard":
        config = load_config(os.getenv("CONFIG_FILE","config/servers.json"))
        db = Database(os.getenv("DATABASE_FILE","data/metrics.sqlite"))
        app = Dashboard(config,db)
        handler = make_handler(role,app,web_root=os.getenv("WEB_ROOT","dist"))
        threading.Thread(target=Collector(config,db).run,daemon=True).start()
        bind = os.getenv("BIND_HOST","127.0.0.1")
        port = int(os.getenv("PORT","3090"))
    else:
        token = secret("READER_TOKEN" if role=="reader" else "GATEWAY_TOKEN")
        app = Reader() if role=="reader" else Gateway()
        handler = make_handler(role,app,token)
        bind = os.getenv("BIND_HOST","0.0.0.0")
        port = int(os.getenv("PORT","8080"))
    if role=="reader":
        server = UnixBoundedServer(os.getenv("READER_SOCKET","/run/metrics/reader.sock"),handler)
    else:
        server = BoundedServer((bind,port),handler)
    def shutdown(*_):
        STOP.set()
        threading.Thread(target=server.shutdown,daemon=True).start()
    signal.signal(signal.SIGTERM,shutdown)
    signal.signal(signal.SIGINT,shutdown)
    LOG.info("%s in ascolto su %s",role,"socket Unix" if role=="reader" else str(port))
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__=="__main__":
    main()
