#!/usr/bin/env bash
# Build and verify the one-folder bundle on Linux: dist/PokerPractice/PokerPractice
# Usage: packaging/build_linux.sh   (uses .venv; run from anywhere)
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
$PY -m pip install -q -r requirements-dev.txt -r requirements-build.txt 2>/dev/null \
  || ~/.local/bin/uv pip install --python .venv -q -r requirements-dev.txt -r requirements-build.txt
$PY -m pytest -q
$PY -m PyInstaller --noconfirm --clean packaging/PokerPractice.spec
DATA=$(mktemp -d)
for run in 1 2; do
  POKER_PRACTICE_DATA_DIR=$DATA QT_QPA_PLATFORM=${QT_QPA_PLATFORM:-offscreen} \
    dist/PokerPractice/PokerPractice --self-test
done
echo "Built and verified: dist/PokerPractice/PokerPractice"
