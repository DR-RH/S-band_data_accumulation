#!/bin/zsh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/../server"

if [[ ! -x ".venv/bin/python" ]]; then
  echo "[ERROR] server/.venv was not found."
  echo "Run setup for the server environment first."
  read -r "?Press Enter to close..."
  exit 1
fi

echo "Starting S-band DB server..."
echo "URL: http://127.0.0.1:8000"
echo "Keep this window open while using the viewer."
echo

.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload

read -r "?Press Enter to close..."

