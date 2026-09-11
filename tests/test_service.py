import contextlib
import http.client
import json
import os
from pathlib import Path
import ssl
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import service as s


@contextlib.contextmanager
def server(handler, tls=None):
    instance = s.BoundedServer(("127.0.0.1", 0), handler)
    if tls:
        instance.socket = tls.wrap_socket(instance.socket, server_side=True)
    worker = threading.Thread(target=instance.serve_forever, daemon=True)
    worker.start()
    try:
        yield instance.server_address[1]
    finally:
        instance.shutdown()
        instance.server_close()
        worker.join()


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = s.Database(Path(self.temp.name) / "db.sqlite")
        self.now = int(time.time()) * 1000
        self.resource = {"source":"app-old","id":"application:1","name":"Example",
                         "kind":"application","project":"Project","state":"running"}
        self.db.inventory("pilot", [self.resource], self.now)

    def tearDown(self):
        self.temp.cleanup()

    def test_overlap_is_idempotent(self):
        rows = [{"time":self.now-1000,"value":12.5}]
        for _ in range(2):
            self.db.ingest("pilot","app-old","cpu",rows,self.now-2000,self.now)
        with self.db.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM samples").fetchone()[0],1)

    def test_error_then_first_success_initializes_both_cursors(self):
        self.db.set_error("pilot","offline","app-old","cpu")
        self.db.ingest("pilot","app-old","cpu",[],self.now-60000,self.now)
        row = self.db.cursor("pilot","app-old","cpu")
        self.assertEqual(row["until"],self.now)
        self.assertEqual(row["backfill"],self.now-60000)
        self.assertIsNone(row["error"])

    def test_failed_response_does_not_advance_cursor(self):
        self.db.ingest("pilot","app-old","cpu",[],self.now-60000,self.now)
        self.db.set_error("pilot","offline","app-old","cpu")
        self.assertEqual(self.db.cursor("pilot","app-old","cpu")["until"],self.now)

    def test_redeploy_keeps_history_and_resource_identity(self):
        old = self.now-120000
        self.db.ingest("pilot","app-old","cpu",[{"time":old,"value":10}],old-1000,old+1000)
        new = {**self.resource, "source":"app-new"}
        self.db.inventory("pilot",[new],self.now)
        self.db.ingest("pilot","app-new","cpu",[{"time":self.now,"value":20}],self.now-1000,self.now)
        entities = self.db.entities("pilot")
        apps = [item for item in entities if item["kind"]=="application"]
        self.assertEqual(len(apps),1)
        self.assertEqual(apps[0]["cpu"],20)
        self.assertEqual(apps[0]["running"],1)
        series = self.db.series("pilot","application:1","cpu",old-1000,self.now+1000)
        self.assertEqual([row["value"] for row in series["samples"]],[10,20])

    def test_missing_memory_never_becomes_zero_or_healthy(self):
        self.db.ingest("pilot","app-old","cpu",[{"time":self.now,"value":0}],self.now-1000,self.now)
        item = next(x for x in self.db.entities("pilot") if x["kind"]=="application")
        self.assertEqual(item["cpu"],0)
        self.assertIsNone(item["memory"])
        self.assertNotEqual(item["status"],"fresh")

    def test_nan_and_out_of_range_samples_rejected(self):
        for row in [{"time":self.now,"value":float("nan")},{"time":self.now+5000,"value":2}]:
            with self.assertRaises(ValueError):
                self.db.ingest("pilot","app-old","cpu",[row],self.now-1000,self.now)
        self.assertIsNone(self.db.cursor("pilot","app-old","cpu"))

    def test_empty_query_has_no_fabricated_zeroes(self):
        self.assertEqual(self.db.series("pilot","server","cpu",0,self.now)["samples"],[])

    def test_parallel_replicas_are_summed(self):
        other = {**self.resource,"source":"app-replica"}
        self.db.inventory("pilot",[self.resource,other],self.now)
        for source in ("app-old","app-replica"):
            self.db.ingest("pilot",source,"cpu",[{"time":self.now,"value":25}],self.now-1000,self.now)
        series = self.db.series("pilot","application:1","cpu",self.now-1000,self.now)
        self.assertEqual(series["samples"][0]["value"],50)

    def test_compaction_preserves_mean_and_peak_and_is_idempotent(self):
        start = ((self.now-8*86400_000)//300_000)*300_000
        rows = [{"time":start+10000,"value":10},{"time":start+20000,"value":90}]
        self.db.ingest("pilot","app-old","cpu",rows,start,start+30000)
        self.db.compact(90,self.now)
        self.db.compact(90,self.now)
        with self.db.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM samples").fetchone()[0],0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM rollups").fetchone()[0],1)
        series=self.db.series("pilot","application:1","cpu",self.now-30*86400_000,self.now)
        self.assertEqual(series["samples"][0]["value"],50)
        self.assertEqual(series["samples"][0]["high"],90)
        self.assertEqual(series["samples"][0]["count"],2)

    def test_partial_replica_metrics_are_not_reported_healthy(self):
        self.db.inventory("pilot",[self.resource,{**self.resource,"source":"missing-replica"}],self.now)
        for metric in s.METRICS:
            self.db.ingest("pilot","app-old",metric,[{"time":self.now,"value":10}],self.now-1000,self.now)
        item=next(x for x in self.db.entities("pilot") if x["id"]=="application:1")
        self.assertEqual(item["status"],"partial")


class BoundaryTests(unittest.TestCase):
    def test_history_source_uses_sentinel_display_name(self):
        item = {"Names": ["/app-uuid-123456"], "Labels": {
            "coolify.name": "app-uuid", "coolify.applicationId": "83"}}
        self.assertEqual(s.identify(item)["source"], "app-uuid")
        self.assertEqual(s.identify(item)["id"], "application:83")
        item["Labels"].pop("coolify.name")
        self.assertEqual(s.identify(item)["source"], "app-uuid-123456")
        item["Labels"]["coolify.name"] = "../unsafe"
        self.assertIsNone(s.identify(item))

    def test_history_rejects_traversal_and_large_ranges(self):
        for query in [
            {"metric":["cpu"],"container":["../secret"],"from":["2026-01-01T00:00:00Z"],"to":["2026-01-01T01:00:00Z"]},
            {"metric":["cpu"],"from":["2026-01-01T00:00:00Z"],"to":["2026-01-02T00:00:00Z"]},
            {"metric":["cpu"],"from":["2026-01-01T00:00:00"],"to":["2026-01-01T01:00:00Z"]},
            {"metric":["cpu","memory"],"from":["0"],"to":["1000"]},
            {"metric":["cpu"],"url":["http://evil"],"from":["0"],"to":["1000"]},
        ]:
            with self.assertRaises(s.Problem):
                s.history_query(query)

    def test_docker_only_allows_two_exact_get_endpoints(self):
        for path in ("/containers/app/exec","/containers/app/json","/images/json","/containers/coolify-sentinel/json?x=1"):
            with self.assertRaises(s.Problem):
                s.docker_read(path)

    def test_reader_rediscovers_ip_and_secret_after_recreation(self):
        def inspection(ip,token):
            return {"NetworkSettings":{"Networks":{"bridge":{"IPAddress":ip}}},
                    "Config":{"Env":["TOKEN="+token,"UNRELATED_SECRET=hidden"]}}
        reader = s.Reader()
        with patch.object(s,"docker_read",side_effect=[inspection("172.17.0.2","old"),inspection("172.17.0.9","new")]) as read:
            self.assertEqual(reader.upstream(),("http://172.17.0.2:8888","old"))
            self.assertEqual(reader.upstream(),("http://172.17.0.2:8888","old"))
            reader.cache_time=0
            self.assertEqual(reader.upstream(),("http://172.17.0.9:8888","new"))
            self.assertEqual(read.call_count,2)

    def test_reader_returns_only_metric_fields(self):
        reader=s.Reader()
        with patch.object(reader,"upstream",return_value=("http://internal:8888","secret")):
            with patch.object(s,"fetch_json",return_value=[{"time":"1000","percent":"123.5","secret":"hidden"}]):
                payload=reader.history({"metric":["cpu"],"from":["0"],"to":["2000"]})
        self.assertEqual(payload["samples"],[{"time":1000,"value":123.5}])
        self.assertNotIn("hidden",json.dumps(payload))

    def test_inventory_does_not_export_docker_environment(self):
        resource=s.identify({"Names":["/web-123"],"Labels":{"coolify.applicationId":"1","coolify.resourceName":"web","secret":"hidden"},"Env":["TOKEN=secret"]})
        self.assertEqual(resource["id"],"application:1")
        self.assertNotIn("hidden",json.dumps(resource))
        self.assertNotIn("TOKEN",json.dumps(resource))

    def test_gateway_http_auth_and_read_only_routes(self):
        class Fixture:
            calls=0
            def inventory(self):
                self.calls+=1
                return {"resources":[]}
        fixture=Fixture()
        with server(s.make_handler("gateway",fixture,"x"*40)) as port:
            conn=http.client.HTTPConnection("127.0.0.1",port)
            for method,path,auth,status in [
                ("GET","/v1/inventory",None,401),
                ("GET","/v1/inventory","wrong",401),
                ("POST","/v1/inventory","x"*40,405),
                ("GET","/containers/json","x"*40,404),
                ("GET","/v1/inventory?url=evil","x"*40,400),
                ("GET","/v1/inventory","x"*40,200),
            ]:
                headers={"Authorization":"Bearer "+auth} if auth else {}
                conn.request(method,path,headers=headers)
                response=conn.getresponse()
                self.assertEqual(response.status,status,(method,path))
                response.read()
            conn.close()
        self.assertEqual(fixture.calls,1)

    def test_dashboard_rejects_dns_rebinding_host(self):
        with server(s.make_handler("dashboard",None,web_root="dist")) as port:
            conn=http.client.HTTPConnection("127.0.0.1",port)
            conn.request("GET","/health",headers={"Host":"attacker.example"})
            response=conn.getresponse()
            self.assertEqual(response.status,403)
            response.read()
            conn.close()


class EndToEndTests(unittest.TestCase):
    def test_tls_gateway_collection_and_offline_catchup(self):
        with tempfile.TemporaryDirectory() as tmp:
            cert,key=Path(tmp)/"cert.pem",Path(tmp)/"key.pem"
            subprocess.run(["openssl","req","-x509","-newkey","rsa:2048","-nodes","-keyout",str(key),
                "-out",str(cert),"-days","1","-subj","/CN=localhost","-addext","subjectAltName=DNS:localhost"],
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
            tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            tls.load_cert_chain(cert,key)
            class Fixture:
                def inventory(self):
                    return {"resources":[]}
                def history(self,query):
                    container,metric,start,end=s.history_query(query)
                    return {"container":container,"metric":metric,"samples":[{"time":end-10000,"value":12 if metric=="cpu" else 104857600}]}
            fixture=Fixture()
            with server(s.make_handler("gateway",fixture,"t"*40),tls) as port:
                db=s.Database(Path(tmp)/"db.sqlite")
                remote={"id":"pilot","name":"Pilot","enabled":True,"url":"https://localhost:"+str(port),"token":"t"*40,"ca_file":str(cert)}
                config={"servers":[remote],"retention_days":90,"poll_seconds":30}
                collector=s.Collector(config,db)
                collector.cycle()
                entity=db.entities("pilot")[0]
                self.assertEqual(entity["cpu"],12)
                self.assertEqual(entity["memory"],104857600)
                self.assertEqual(entity["status"],"fresh")
                old=db.cursor("pilot","","cpu")["until"]
                def offline(*_):
                    raise s.Problem(502,"offline")
                with patch.object(collector,"request",side_effect=offline):
                    collector.cycle()
                self.assertEqual(db.cursor("pilot","","cpu")["until"],old)
                collector.cycle()
                with db.connect() as connection:
                    self.assertIsNone(connection.execute("SELECT error FROM status").fetchone()[0])
                # Default TLS verification must reject our untrusted test certificate.
                with self.assertRaises(s.Problem):
                    s.fetch_json(remote["url"]+"/v1/inventory",remote["token"])
                # No credentials in the dashboard's browser-facing payload.
                overview=s.Dashboard(config,db).overview()
                self.assertNotIn("token",json.dumps(overview))
                self.assertNotIn("ca_file",json.dumps(overview))

    def test_redirect_is_not_followed(self):
        from http.server import BaseHTTPRequestHandler
        class Destination(BaseHTTPRequestHandler):
            calls=0
            def do_GET(self):
                Destination.calls+=1
                self.send_response(200);self.end_headers();self.wfile.write(b"{}")
            def log_message(self,*_): pass
        with server(Destination) as destination:
            class Redirect(BaseHTTPRequestHandler):
                def do_GET(self):
                    self.send_response(302)
                    self.send_header("Location","http://127.0.0.1:"+str(destination)+"/steal")
                    self.end_headers()
                def log_message(self,*_): pass
            with server(Redirect) as source:
                with self.assertRaises(s.Problem):
                    s.fetch_json("http://127.0.0.1:"+str(source),"sensitive")
            self.assertEqual(Destination.calls,0)


if __name__=="__main__":
    unittest.main()
