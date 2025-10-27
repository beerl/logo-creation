#!/bin/bash
set -euo pipefail

# Ensure Homebrew cairo is discoverable for Python (macOS)
export DYLD_FALLBACK_LIBRARY_PATH="/opt/homebrew/lib:${DYLD_FALLBACK_LIBRARY_PATH:-}"

# Activate venv
if [ -d .venv ]; then
  source .venv/bin/activate
else
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt --no-input
fi

# Start app (dev)
export FLASK_APP=app.py
export FLASK_ENV=development
python app.py




