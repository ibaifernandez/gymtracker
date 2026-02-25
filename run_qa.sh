#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

if [[ -x ".venv/bin/python" ]]; then
  PY=".venv/bin/python"
else
  PY="python3"
fi

echo "== Unit/API tests =="
"$PY" -m unittest discover -s tests -p 'test_*.py' -v

echo
echo "== Stress tests =="
"$PY" tests/stress_http.py --total "${STRESS_TOTAL:-1500}" --workers "${STRESS_WORKERS:-40}"

echo
echo "== Playwright E2E =="
if [[ -d "node_modules/@playwright/test" ]]; then
  npm run test:e2e
else
  echo "SKIP: Playwright no instalado (falta node_modules/@playwright/test)."
  echo "Cuando haya red disponible: npm install && npx playwright install --with-deps"
fi
