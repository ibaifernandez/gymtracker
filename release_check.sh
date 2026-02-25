#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

if [[ -x ".venv/bin/python" ]]; then
  PY=".venv/bin/python"
else
  PY="python3"
fi

echo "== Release Gate: Unit/API =="
"$PY" -m unittest discover -s tests -p 'test_*.py' -v

echo
echo "== Release Gate: Stress =="
"$PY" tests/stress_http.py --total "${STRESS_TOTAL:-1500}" --workers "${STRESS_WORKERS:-40}"

echo
echo "== Release Gate: Playwright E2E =="
if [[ ! -d "node_modules/@playwright/test" ]]; then
  echo "ERROR: falta Playwright en node_modules."
  echo "Ejecuta: npm install && npx playwright install --with-deps"
  exit 1
fi
npm run test:e2e

echo
echo "== Release Gate OK =="
echo "Checklist minima cumplida: unit + stress + e2e."
