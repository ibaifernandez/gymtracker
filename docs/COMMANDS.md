# Comandos útiles (operación diaria)

Referencia rápida de comandos para limpiar datos, poblar demo, correr QA y arrancar la app.

## 1) Datos (lo más importante)

### `npm run data:clear`
Borra toda la data local de la app: check-ins, entrenos, fotos, suplementos y planes.

### `npm run data:seed:90`
Resetea y carga **90 días de solo check-ins** (sin entrenos planificados ni suplementos).

### `npm run data:seed:90:full`
Resetea y carga **90 días** de check-ins + entrenos demo.

### `npm run data:seed`
Resetea y carga **45 días demo aleatorios** (check-ins + entrenos).

### `npm run seed:demo`
Carga demo fija de 45 días (perfil `fatloss`, semilla fija), **sin reset total**.

### `npm run seed:demo:reset`
Igual que el anterior, pero borrando antes.

## 2) Tests / QA

### `source .venv/bin/activate && python -m unittest tests/test_backend.py`
Corre tests backend (unit/integration Flask).

### `npm run test:e2e`
Playwright headless.

### `npm run test:e2e:headed`
Playwright con navegador visible.

### `npm run test:e2e:ui`
Playwright UI interactiva.

### `npm run release:check`
Chequeo global de release.

## 3) Arranque app

### `python app.py`
Arranque estándar y portable del proyecto.

### Scripts locales opcionales
Si quieres, puedes mantener scripts personales locales (`run.command`, `start_tracker.zsh`) para automatizar tu flujo en tu máquina, pero no forman parte del repositorio público.

## 4) Utilidades Python directas

### `python3 tools/clear_data.py --vacuum`
Limpia data y compacta la base SQLite.

### `python3 tools/seed_demo_data.py --help`
Muestra todas las opciones de seed (`--days`, `--profile`, `--seed`, `--diet-only`, etc.).

## 5) Nota importante (zsh)

No uses paréntesis al final del comando.

- Correcto: `npm run data:seed:90`
- Incorrecto: `npm run data:seed:90 (line 90)`

El segundo da error de zsh: `number expected`.
