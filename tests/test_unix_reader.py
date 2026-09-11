import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import service as s


class UnixReaderTests(unittest.TestCase):
    def test_gateway_reads_through_unix_socket_with_authentication(self):
        class Fixture:
            def inventory(self):
                return {"resources": [], "observed_at": 1234}

        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "reader.sock")
            token = "fixture-token-not-a-real-secret-12345"
            server = s.UnixBoundedServer(path, s.make_handler("reader", Fixture(), token))
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                self.assertEqual(os.stat(path).st_mode & 0o777, 0o660)
                with patch.dict(os.environ, {"READER_SOCKET": path, "READER_TOKEN": token}):
                    self.assertEqual(s.reader_json("/health")["role"], "reader")
                    self.assertEqual(s.Gateway().inventory(), {"resources": [], "observed_at": 1234})
                    with self.assertRaises(s.Problem):
                        s.reader_json("/v1/inventory", "wrong-token")
                    with self.assertRaises(s.Problem):
                        s.reader_json("/containers/json", token)
            finally:
                server.shutdown()
                server.server_close()
                worker.join()
