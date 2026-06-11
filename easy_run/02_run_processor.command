#!/bin/zsh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/../processor"

if [[ ! -x ".venv/bin/python" ]]; then
  echo "[ERROR] processor/.venv was not found."
  echo "Run setup for the processor environment first."
  read -r "?Press Enter to close..."
  exit 1
fi

mkdir -p input/unprocessed

echo "Running S-band processor..."
echo "Input folder: processor/input/unprocessed"
echo "DB server: http://127.0.0.1:8000"
echo

.venv/bin/python ./run --no-move

echo
echo "Done. Open the viewer and press Search."
read -r "?Press Enter to close..."

