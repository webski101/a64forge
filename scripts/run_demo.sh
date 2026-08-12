#!/usr/bin/env bash
set -euo pipefail
export A64FORGE_DEV_MODE="${A64FORGE_DEV_MODE:-true}"
source .venv/bin/activate
a64forge serve --host 0.0.0.0 --port 8640

