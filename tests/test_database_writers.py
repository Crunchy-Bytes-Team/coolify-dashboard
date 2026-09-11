"""A slow historical write must not make a concurrent live sample fail SQLITE_BUSY."""
from contextlib import contextmanager
import tempfile
import threading
import time
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import service


class WriterTests(unittest.TestCase):
    def test_live_ingest_waits_for_another_local_writer(self):
        entered, release = threading.Event(), threading.Event()

        class TestDatabase(service.Database):
            @contextmanager
            def connect(self):
                with super().connect() as connection:
                    connection.execute('PRAGMA busy_timeout=10')
                    def hold():
                        entered.set()
                        if not release.wait(3):
                            raise RuntimeError('Test writer was not released')
                        return 1
                    connection.create_function('hold_writer',0,hold)
                    yield connection

        with tempfile.TemporaryDirectory() as directory:
            db=TestDatabase(Path(directory)/'metrics.sqlite')
            with db.connect() as connection:
                connection.execute("CREATE TRIGGER slow_history AFTER INSERT ON samples WHEN NEW.source='history' BEGIN SELECT hold_writer(); END")
            now=int(time.time()*1000)
            def ingest(source):
                db.ingest('host',source,'cpu',[{'time':now,'value':50}],now-1000,now)
            with ThreadPoolExecutor(max_workers=2) as pool:
                historical=pool.submit(ingest,'history')
                try:
                    self.assertTrue(entered.wait(2))
                    current=pool.submit(ingest,'live')
                    # Longer than SQLite's busy timeout: the live writer must queue.
                    time.sleep(.1)
                finally:
                    release.set()
                historical.result(timeout=2)
                current.result(timeout=2)
            with db.connect() as connection:
                self.assertEqual(connection.execute('SELECT COUNT(*) FROM samples').fetchone()[0],2)
