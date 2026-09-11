import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import service as s


class MemoryPercentageTests(unittest.TestCase):
    def test_latest_capacity_tracks_sample_and_ignores_older_backfill(self):
        with tempfile.TemporaryDirectory() as directory:
            db = s.Database(Path(directory) / "metrics.sqlite")
            now = int(time.time()*1000)
            db.inventory("node", [], now)
            db.ingest("node", "", "memory", [{"time":now,"value":80,"total":100}],now-1000,now)
            db.ingest("node", "", "memory", [{"time":now-2000,"value":10,"total":200}],now-3000,now-1000,True)
            row = db.entities("node", "server")[0]
            self.assertEqual(row["memory_percent"],80)
            self.assertEqual(row["memory_total"],100)
            db.ingest("node", "", "memory", [{"time":now+1000,"value":90}],now,now+1000)
            self.assertIsNone(db.entities("node", "server")[0]["memory_percent"])

    def test_reader_preserves_only_valid_host_capacity(self):
        now = int(time.time())*1000
        query={"container":[""],"metric":["memory"],"from":[s.iso(now-1000)],"to":[s.iso(now)]}
        reader=s.Reader()
        for total, expected in ((100,100),(0,None),(-1,None),(float("nan"),None),(20,None),("invalid",None)):
            with self.subTest(total=total), patch.object(reader,"upstream",return_value=("http://fixture","token")), patch.object(s,"fetch_json",return_value=[{"time":now,"used":80,"total":total}]):
                sample=reader.history(query)["samples"][0]
                self.assertEqual(sample["value"],80)
                self.assertEqual(sample.get("total"),expected)
