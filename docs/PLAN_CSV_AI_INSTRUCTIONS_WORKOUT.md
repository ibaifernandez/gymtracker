# Instrucciones IA para CSV de Entreno Planificado (Gym Tracker) — v2

## Propósito
Generar un archivo CSV **listo para importar** que siga **exactamente** la estructura de `plan_workout_template.csv` (inamovible).

## Insumos obligatorios
1) `plan_workout_template.csv`  
2) Este documento (`PLAN_CSV_AI_INSTRUCTIONS_WORKOUT.md`)

## Contrato de salida (estricto)
- Cuando produzcas el entregable final: **responde SOLO con CSV crudo** (sin Markdown, sin texto extra).
- La **primera línea** debe ser la cabecera oficial **exacta** y en el **mismo orden**.
- No renombres columnas, no reordenes, no agregues columnas, no agregues comentarios.
- Separador: coma. Codificación: UTF-8.

## Cabecera oficial (inamovible)
log_date,session_type,warmup,class_sessions,cardio,mobility_cooldown,additional_exercises,notes,exercise_1_name,exercise_1_sets,exercise_1_reps_min,exercise_1_reps_max,exercise_1_weight_kg,exercise_1_rpe,exercise_1_intensity_target,exercise_1_progression_weight_rule,exercise_1_progression_reps_rule,exercise_2_name,exercise_2_sets,exercise_2_reps_min,exercise_2_reps_max,exercise_2_weight_kg,exercise_2_rpe,exercise_2_intensity_target,exercise_2_progression_weight_rule,exercise_2_progression_reps_rule,exercise_3_name,exercise_3_sets,exercise_3_reps_min,exercise_3_reps_max,exercise_3_weight_kg,exercise_3_rpe,exercise_3_intensity_target,exercise_3_progression_weight_rule,exercise_3_progression_reps_rule,exercise_4_name,exercise_4_sets,exercise_4_reps_min,exercise_4_reps_max,exercise_4_weight_kg,exercise_4_rpe,exercise_4_intensity_target,exercise_4_progression_weight_rule,exercise_4_progression_reps_rule,exercise_5_name,exercise_5_sets,exercise_5_reps_min,exercise_5_reps_max,exercise_5_weight_kg,exercise_5_rpe,exercise_5_intensity_target,exercise_5_progression_weight_rule,exercise_5_progression_reps_rule,exercise_6_name,exercise_6_sets,exercise_6_reps_min,exercise_6_reps_max,exercise_6_weight_kg,exercise_6_rpe,exercise_6_intensity_target,exercise_6_progression_weight_rule,exercise_6_progression_reps_rule

## Modelo de datos esperado
- **1 fila = 1 sesión**.
- Puede haber **múltiples filas** con el mismo `log_date` (p. ej., “clase” + “pesas” el mismo día).
- `session_type`: solo `clase` o `pesas` (minúsculas).

## Reglas de negocio críticas
### Si `session_type=clase`
- Deja **vacías** TODAS las columnas `exercise_*` (desde `exercise_1_name` hasta `exercise_6_progression_reps_rule`).
- Usa:
  - `class_sessions` para el/los nombres de la clase (si hay más de una en esa sesión, separa por `; `).
  - `warmup`, `cardio`, `mobility_cooldown`, `additional_exercises`, `notes` solo si aplica (texto breve sin saltos de línea).

### Si `session_type=pesas`
- Puedes completar `exercise_*`.
- `class_sessions` debe ir vacío (salvo que el host defina explícitamente otra convención).
- `warmup`, `mobility_cooldown` y `notes` pueden usarse para contexto.

## Reglas `exercise_*` (solo filas `pesas`)
- `exercise_*_name`: texto (≤ 90 caracteres recomendado).
- `exercise_*_sets`: entero **1 a 12**. Prohibido: rangos (`3-4`), formatos (`3x10`).
- `exercise_*_reps_min` y `exercise_*_reps_max`: enteros **1 a 100**, con `reps_min <= reps_max`.
- `exercise_*_weight_kg`: decimal **0 a 1000** (puede ir vacío si es peso corporal).
- `exercise_*_rpe`: decimal **1 a 10** (puede ir vacío si no se usa RPE).
- `exercise_*_intensity_target`: texto ≤ 140 (p. ej., “técnica limpia; RPE 7”).
- `exercise_*_progression_weight_rule` y `exercise_*_progression_reps_rule`: texto ≤ 240 (reglas claras y accionables).

## Flujo estándar (multi‑turn)
1) **Recibir objetivos y contexto** del usuario.
2) Si falta información crítica para diseñar un plan seguro/importable: emitir **bloque `<missing_critical_data>`** y detener la generación.
3) Tras recibir las respuestas en el formato pedido: generar el CSV final.

### Preguntas críticas mínimas (formato de respuesta obligatorio)
Usa **máximo 5 preguntas**. Cada pregunta pide un objeto JSON para minimizar fricción.

1) Rango de fechas del plan (incluye ambos)  
Formato esperado: `{"start_date":"AAAA-MM-DD","end_date":"AAAA-MM-DD"}`

2) Estructura semanal por día (múltiples sesiones permitidas; `[]` = descanso)  
Formato esperado: `{"mon":["clase","pesas"],"tue":["clase","pesas"],"wed":["clase","pesas"],"thu":["clase","pesas"],"fri":["clase","pesas"],"sat":[],"sun":["clase","pesas"]}`

3) Equipamiento disponible principal  
Formato esperado: `{"equipment":{"A":"gimnasio_completo","B":"mancuernas_banco_bandas","C":"casa_sin_cargas"}}`

4) Experiencia y restricciones  
Formato esperado: `{"strength_level":{"A":"principiante","B":"intermedio","C":"avanzado"},"injuries_or_limitations":["..."],"session_duration_min":{"clase":N,"pesas":N}}`

5) Objetivo y preferencias de enfoque  
Formato esperado: `{"primary_goal":"...","avoid_emphasis":["..."],"prefer_emphasis":["..."],"class_catalog_assumption":{"A":"todas_disponibles","B":"indicar_preferidas"},"preferred_classes_if_B":["..."]}`

## Reglas de programación (entreno)
- Mantener volumen compatible con el nivel (`strength_level`) y con `session_duration_min`.
- Priorizar técnica y progresión simple (reglas en `exercise_*_progression_*_rule`).
- Si hay restricciones/incomodidades no resueltas, no “adivinar”: deja ejercicios vacíos o sustitúyelos por variantes seguras y explica en `notes`.

## Validación final (obligatoria antes de entregar)
- Cabecera exacta y orden exacto.
- Fechas válidas `AAAA-MM-DD`.
- `session_type` solo `clase` o `pesas`.
- En filas `clase`: **todas** las `exercise_*` vacías.
- En `*_sets`: solo enteros 1–12 (sin rangos ni “3x10”).
- CSV parseable (coma, UTF‑8).
- Cero texto fuera del CSV.
