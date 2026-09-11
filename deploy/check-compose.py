"""Validate the Docker configuration after Coolify materializes bind-mount files."""
from pathlib import Path
import os
import subprocess

root = Path(__file__).resolve().parents[1]
source = (root / "deploy/coolify-gateway.yaml").read_text()
# `content` is a Coolify extension, consumed before invoking Docker Compose.
materialized = source.replace("        content: *metrics-code\n", "")
subprocess.run(
    ["docker", "compose", "--env-file", "/dev/null",
     "-f", "-", "config", "--quiet"],
    input=materialized, text=True, cwd=root, check=True,
    env={**os.environ, "METRICS_GATEWAY_TOKEN": "validation-placeholder-gateway-not-a-secret",
         "METRICS_READER_TOKEN": "validation-placeholder-reader-not-a-secret"},
)
print("Compose valido dopo materializzazione dei file Coolify.")
