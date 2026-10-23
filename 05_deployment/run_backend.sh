#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../02_web_service/backend"
exec python -m uvicorn app:app --host 127.0.0.1 --port 8000
