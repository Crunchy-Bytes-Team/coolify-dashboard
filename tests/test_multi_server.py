import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
from pathlib import Path

import service as s


class MultiServerTests(unittest.TestCase):
    def test_live_polling_continues_while_history_is_blocked(self):
        stop, history_started, refreshed = threading.Event(), threading.Event(), threading.Event()
        cfg = {"servers": [{"id": "node", "enabled": True}], "poll_seconds": 0.1, "retention_days": 90}
        collector = s.Collector(cfg, Mock())

        def current(servers, include_history):
            self.assertFalse(include_history)
            if history_started.is_set():
                refreshed.set()

        def historical(server):
            history_started.set()
            try:
                self.assertTrue(refreshed.wait(3), "Historical downloads blocked live refresh")
            finally:
                stop.set()

        collector.collect_servers = current
        collector.collect_backfill = historical
        with patch.object(s, "STOP", stop):
            collector.run()
        self.assertTrue(refreshed.is_set())

    def test_overview_keeps_server_metrics_and_counts_distinct_applications(self):
        with tempfile.TemporaryDirectory() as directory:
            db = s.Database(Path(directory) / "metrics.sqlite")
            now = int(s.time.time()) * 1000
            rows = [{"source": name, "id": "application:1", "name": "Replicated app",
                     "kind": "application", "project": "Example", "state": "running"}
                    for name in ("replica-a", "replica-b")]
            db.inventory("node", rows, now)
            for source, value in (("", 12), ("replica-a", 90), ("replica-b", 80)):
                for metric in s.METRICS:
                    db.ingest("node", source, metric, [{"time": now, "value": value}], now-1000, now)
            config = {"servers": [{"id": "node", "name": "Node", "enabled": True}],
                      "poll_seconds": 30, "retention_days": 90}
            row = s.Dashboard(config, db).overview()["servers"][0]
            self.assertEqual(row["resources"], 1)
            self.assertEqual(row["metrics"]["cpu"], 12)
            self.assertEqual(row["metrics"]["status"], "fresh")

    def test_slow_failed_host_does_not_block_healthy_host(self):
        healthy_seen = threading.Event()
        overlap = []

        def request(url, token, ca):
            if url.startswith("https://slow"):
                overlap.append(healthy_seen.wait(3))
                raise s.Problem(502, "Server non raggiungibile.")
            healthy_seen.set()
            return {"resources": []}

        with tempfile.TemporaryDirectory() as directory:
            db = s.Database(Path(directory) / "metrics.sqlite")
            config = {"retention_days": 90, "servers": [
                {"id": name, "url": "https://" + name, "token": "x" * 64,
                 "enabled": True} for name in ("slow", "healthy")
            ]}
            s.Collector(config, db, request=request).cycle()
            self.assertEqual(overlap, [True])
            with db.connect() as conn:
                states = {row["server"]: dict(row) for row in conn.execute("SELECT * FROM status")}
            self.assertIsNone(states["healthy"]["error"])
            self.assertIsNotNone(states["healthy"]["contacted"])
            self.assertIsNotNone(states["slow"]["error"])


if __name__ == "__main__":
    unittest.main()
