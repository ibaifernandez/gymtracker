# Gym Tracker

Aplicacion local (Flask + SQLite + HTML/CSS/JS) para registrar check-ins diarios, sesiones de entrenamiento y plan diario (vista `Planes`).

## Que hace

- Check-in diario: sueno, calidad, pasos, peso, cintura, cadera, creatina, alcohol y foto opcional.
- Rutina por sesiones: varias sesiones el mismo dia, tipo (`clase`/`pesas`), RPE, ejercicios y notas.
- Plan diario (separado del registro real): dieta del dia + sesiones/ejercicios sugeridos, importados por CSV.
- Adherencia del plan por fecha (escala `1 / 0.5 / 0`) sin sobrescribir tus logs reales, con histórico rápido `7/15/30` y resumen semanal.
- KPIs por rango libre y modo automatico de 7 dias naturales.
- Grafica simple de rendimiento (peso, WHR, sueno, pasos) + informe rapido en PNG.
- Lightbox de fotos con miniaturas y comparador antes/despues.
- CTA rapidos `Ver todo` para abrir bloques completos y flujo `Reportar bug` con diagnostico copiable.
- Importacion CSV de check-ins con preview (valid/conflict/invalid).
- Exportacion CSV de registros (`check-ins.csv`), entrenos (`workout.csv`) y suplementos (`supplements.csv`).
- Backup/restore local (`tracker.db` + `uploads/`).
- Auth local opcional por clave unica (sin usuario).

## Requisitos

- Python 3.9+ (recomendado: 3.13).
- `pip`.
- Node.js 20+ (solo para Playwright/E2E).

## Arranque rapido

```bash
git clone https://github.com/ibaifernandez/gymtracker.git
cd gymtracker
python3 -m venv .venv
source .venv/bin/activate
pip install flask werkzeug
npm install
python app.py
```

Abre: `http://127.0.0.1:5050`

## Configuracion por entorno (opcional)

Archivo sugerido: `.env.local` (cargado automáticamente por la app al arrancar).

Variables principales:

- `TRACKER_HOST` (default: `127.0.0.1`)
- `TRACKER_PORT` (default: `5050`)
- `TRACKER_DB_PATH` (default: `tracker.db`)
- `TRACKER_UPLOAD_ROOT` (default: `static/uploads`)
- `TRACKER_SECRET_KEY`
- `TRACKER_AUTH_ENABLED=1` para exigir login
- `TRACKER_AUTH_PASSWORD_HASH` hash Werkzeug (`scrypt:...`)
- `TRACKER_PHOTO_COMPRESSION_ENABLED` (default `1`)
- `TRACKER_PHOTO_MAX_SIDE` (default `1600`)
- `TRACKER_PHOTO_QUALITY` (default `82`)
- `TRACKER_PHOTO_PREFER_WEBP` (default `1`)

Nota: para compresion real de imagenes, instala Pillow:

```bash
source .venv/bin/activate
pip install Pillow
```

## Scripts utiles

```bash
# QA completo de release
npm run release:check

# Solo E2E
npm run test:e2e

# Limpiar datos locales
npm run data:clear

# Poblar demo aleatoria
npm run data:seed
```

## Plan diario por CSV (plantillas oficiales)

El modulo `Planes` usa 2 CSV:

- `plan_diet_template.csv`
- `plan_workout_template.csv` (sesiones + ejercicios en un unico archivo)

Puedes descargarlos desde la GUI (modal de importacion de plan) o por endpoint:

- `/export/template/plan-diet.csv`
- `/export/template/plan-workout.csv`

Reglas clave del CSV de entreno:

1. No se escribe `session_id`: la app lo deriva por fecha segun orden de filas.
2. Se permiten varias filas con la misma fecha (varias sesiones el mismo dia).
3. Si `session_type=clase`, las columnas de ejercicios se ignoran con aviso.
4. Si `session_type=pesas`, los ejercicios son opcionales.

Compatibilidad legacy: siguen disponibles
`/export/template/plan-workout-sessions.csv` y `/export/template/plan-workout-exercises.csv`.

## Testing

Backend:

```bash
source .venv/bin/activate
python -m unittest tests/test_backend.py
```

E2E (Playwright):

```bash
npm install
npx playwright install --with-deps
npm run test:e2e
```

## Documentacion

- Backlog SSOT: [`docs/BACKLOG.md`](docs/BACKLOG.md)
- Mapa del proyecto: [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md)
- Operacion local: [`docs/LOCAL_OPERATIONS.md`](docs/LOCAL_OPERATIONS.md)
- Comandos rápidos: [`docs/COMMANDS.md`](docs/COMMANDS.md)
- Guía IA CSV dieta: [`docs/PLAN_CSV_AI_INSTRUCTIONS_DIET.md`](docs/PLAN_CSV_AI_INSTRUCTIONS_DIET.md)
- Guía IA CSV entreno: [`docs/PLAN_CSV_AI_INSTRUCTIONS_WORKOUT.md`](docs/PLAN_CSV_AI_INSTRUCTIONS_WORKOUT.md)
- System prompt IA CSV: [`docs/PLAN_CSV_AI_SYSTEM_PROMPT.md`](docs/PLAN_CSV_AI_SYSTEM_PROMPT.md)

## Nota para contribuidores con IA

`AGENTS.md` es un archivo local/no versionado por diseño. Cada persona debe crear su propio archivo si quiere usar su propio flujo con agentes.

## Archivos locales opcionales (no versionados)

Si quieres tener atajos personales de arranque en tu máquina, puedes crear archivos locales como:

- `run.command`
- `start_tracker.zsh`

No forman parte del repositorio público por diseño.

## Licencia

Este proyecto se publica bajo **The Unlicense** (dominio público).
Puedes usarlo, copiarlo, modificarlo y redistribuirlo sin restricciones.
