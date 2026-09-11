import http.client
import unittest
from unittest.mock import patch

import service
from test_service import server


class DashboardHostTests(unittest.TestCase):
    def status(self, port, host):
        connection = http.client.HTTPConnection("127.0.0.1", port)
        connection.request("GET", "/health", headers={"Host": host})
        response = connection.getresponse()
        response.read()
        connection.close()
        return response.status

    def test_private_hostname_is_explicitly_allowed(self):
        with patch.dict("os.environ", {"DASHBOARD_ALLOWED_HOSTS": "dashboard.example.com"}):
            with server(service.make_handler("dashboard", None)) as port:
                self.assertEqual(self.status(port, "dashboard.example.com:9443"), 200)
                self.assertEqual(self.status(port, "127.0.0.1:3090"), 200)
                self.assertEqual(self.status(port, "dashboard.example.com.evil.test"), 403)
                self.assertEqual(self.status(port, "other.example.com"), 403)

    def test_defaults_remain_local_only(self):
        with patch.dict("os.environ", {"DASHBOARD_ALLOWED_HOSTS": ""}):
            with server(service.make_handler("dashboard", None)) as port:
                self.assertEqual(self.status(port, "localhost:3090"), 200)
                self.assertEqual(self.status(port, "dashboard.example.com:9443"), 403)
