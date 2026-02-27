# QA manual · Portada (v1.0.0.1 local)

Checklist específico para validar la nueva portada visual (`/portada`) sin tocar lógica interna de API o base de datos.

## Alcance

- Solo UX/UI y navegación de la portada.
- No cubre CRUD de check-ins, entrenos, planes ni backup/restore.

## Precondiciones

1. App levantada en local (`python app.py` o `run.command`).
2. Navegador desktop y móvil (o emulación responsive).
3. Auth local probada en dos modos:
   - `TRACKER_AUTH_ENABLED=0` (o sin hash) para validar fallback.
   - `TRACKER_AUTH_ENABLED=1` + hash para validar login real.

## Casos de prueba

### COV-001 · Carga base de portada

- Paso: abrir `/portada`.
- Esperado:
  - status 200.
  - se ve hero principal.
  - aparecen bloques: `Data Sovereignty Command Center`, `No Vendor Lock-In Proof`, `QA Shield Wall`.
  - se ve mockup de móvil a la derecha (desktop).

### COV-002 · Botón `Abrir dashboard local`

- Paso: click en `Abrir dashboard local`.
- Esperado:
  - navega a `/`.
  - dashboard de Gym Tracker visible.

### COV-003 · Botón `Login local` con auth desactivada

- Precondición: auth desactivada.
- Paso: click en `Login local`.
- Esperado:
  - navegación funcional sin error.
  - redirección a `/` (fallback normal del sistema).

### COV-004 · Botón `Login local` con auth activada

- Precondición: auth activada (`TRACKER_AUTH_ENABLED=1` + hash válido).
- Paso: click en `Login local`.
- Esperado:
  - navega a `/login`.
  - formulario de clave visible.

### COV-005 · Responsive móvil (390x844)

- Paso: abrir `/portada` en ancho 390.
- Esperado:
  - layout en una columna.
  - botones de cabecera visibles y clicables.
  - sin scroll horizontal accidental.

### COV-006 · Contraste y legibilidad

- Paso: revisar portada en brillo normal.
- Esperado:
  - títulos y cifras se leen sin esfuerzo.
  - métricas principales (`0`, `NONE`, `1.24 ms`, `100% LOCAL`, `97/97`) son distinguibles.

### COV-007 · Estabilidad de navegación

- Paso: alternar 10 veces entre `/portada`, `/`, `/help`.
- Esperado:
  - sin bloqueos JS.
  - sin pantalla en blanco.
  - navegación consistente.

## Criterio de aceptación

- Todos los casos `COV-001` a `COV-007` en verde.
- Si falla uno crítico (`COV-002`, `COV-004`, `COV-005`), no promover a release público.
