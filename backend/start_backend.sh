#!/usr/bin/env bash
set -e
cd /home/sunrise/vision-memory-agent/backend
source .venv/bin/activate
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
