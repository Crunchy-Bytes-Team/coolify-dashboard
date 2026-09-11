"""Keep the pasted deployment code aligned with the tested implementation."""
import ast
from pathlib import Path
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DeploymentBundleTests(unittest.TestCase):
    def test_remote_functions_match_tested_implementation(self):
        def definitions(path):
            return {node.name: ast.dump(node) for node in ast.parse(path.read_text()).body
                    if isinstance(node, (ast.ClassDef, ast.FunctionDef))}
        source = definitions(ROOT / "service.py")
        remote = definitions(ROOT / "deploy/gateway-service.py")
        for name, definition in remote.items():
            if name != "main":
                with self.subTest(name=name):
                    self.assertEqual(source[name], definition)

    def test_embedded_source_matches_remote_file(self):
        compose = (ROOT / "deploy/coolify-gateway.yaml").read_text()
        embedded = textwrap.dedent(compose.split("x-metrics-code: &metrics-code |\n", 1)[1].split("\n# Deploy only", 1)[0]).replace("$$", "$")
        self.assertEqual(embedded.strip(), (ROOT / "deploy/gateway-service.py").read_text().strip())

    def test_portable_bundle_uses_the_same_verified_reader(self):
        compose = (ROOT / "deploy/coolify-gateway-portable.yaml").read_text()
        embedded = textwrap.dedent(compose.split("x-metrics-code: &metrics-code |\n", 1)[1].split("\nservices:\n", 1)[0])
        self.assertEqual(embedded.strip(), (ROOT / "deploy/gateway-service.py").read_text().strip())
        self.assertNotIn("type: bind", compose)
        self.assertEqual(compose.count("METRICS_SOURCE: *metrics-code"), 2)
