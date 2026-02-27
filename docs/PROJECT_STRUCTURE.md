# Estructura del proyecto

Mapa rápido de carpetas y archivos relevantes para operar y extender Gym Tracker.

## Raíz del proyecto

- `app.py`: servidor Flask, rutas HTML/API, esquema SQLite y lógica principal.
- `README.md`: guía principal de instalación, uso y testing.
- `package.json`: scripts npm (E2E, release check, seed/clear data).
- `playwright.config.js`: configuración de Playwright.
- `run_qa.sh`: runner de QA local.
- `release_check.sh`: chequeo de release (backend + stress + E2E).
- `.gitignore`: exclusiones de git.
- `.env.local` (opcional, no versionado): variables locales y secretos.
- `AGENTS.md` (opcional, no versionado): instrucciones locales para uso con agentes/IA.

## Backend

- `app.py`
  - Endpoints HTML (`/`, `/help`, `/changelog`, `/login`).
  - Endpoints API (`/api/*`) para check-ins, entrenos, suplementos, planes y backups.
  - Endpoints de export/import CSV y backup.

## Frontend (templates)

- `templates/index.html`: shell principal del dashboard SPA.
- `templates/login.html`: pantalla de login (si auth está activa).
- `templates/help.html`: manual de uso para usuario final.
- `templates/help.txt`: referencia histórica/auxiliar de ayuda.
- `templates/changelog.html`: historial de versiones.

### Parciales del dashboard

- `templates/partials/index/topbar.html`
- `templates/partials/index/mobile_nav.html`
- `templates/partials/index/utility_ui.html`
- `templates/partials/index/view_home.html`
- `templates/partials/index/view_checkin.html`
- `templates/partials/index/view_supplements.html`
- `templates/partials/index/view_workouts.html`
- `templates/partials/index/view_progress.html`
- `templates/partials/index/view_plans.html`
- `templates/partials/index/view_data.html`
- `templates/partials/index/modals.html`
- `templates/partials/index/footer.html`

## Frontend estático

- `static/styles.css`: estilos globales (claro/oscuro, tablas, modales, planes, etc.).
- `static/app.js`: lógica UI principal (render, formularios, import/export, modales).
- `static/help.js`: interacciones del manual de ayuda.
- `static/changelog.js`: interacciones de changelog.
- `static/login.js`: UX del login.

## Tests

- `tests/test_backend.py`: suite backend/API (unittest).
- `tests/stress_http.py`: stress test HTTP concurrente.
- `tests/e2e/tracker.spec.js`: pruebas E2E Playwright.
- `tests/fixtures/photo.png`: fixture de imagen para tests.

## Utilidades de datos

- `tools/clear_data.py`: limpia tablas y uploads locales.
- `tools/seed_demo_data.py`: genera dataset demo (determinista o aleatorio).

## Documentación en `docs/`

- `docs/BACKLOG.md`: backlog SSOT actual.
- `docs/PROJECT_STRUCTURE.md`: este documento.
- `docs/LOCAL_OPERATIONS.md`: operación local y acceso remoto opcional.
- `docs/COMMANDS.md`: referencia diaria de comandos.
- `docs/PLAN_CSV_AI_INSTRUCTIONS_DIET.md`: instrucciones IA para CSV de dieta.
- `docs/PLAN_CSV_AI_INSTRUCTIONS_WORKOUT.md`: instrucciones IA para CSV de entreno planificado.
- `docs/PLAN_CSV_AI_SYSTEM_PROMPT.md`: prompt de sistema para el flujo IA (dieta + entreno).
- `docs/QA_MANUAL_PORTADA_V1_0_0_1.md`: checklist QA específico de la portada visual `/portada`.

## Runtime local (no versionado)

- `tracker.db`: base SQLite local.
- `static/uploads/`: fotos subidas por el usuario.
- `test-results/`: artefactos de Playwright.
- `run.command` (opcional, no versionado): launcher local personal (macOS).
- `start_tracker.zsh` (opcional, no versionado): script local personal de arranque.
- `.tmp/`, `.venv/`, `node_modules/`, `__pycache__/`: entorno/cache regenerable.
