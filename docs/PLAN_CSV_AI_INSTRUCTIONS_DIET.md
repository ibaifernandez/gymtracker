# Instrucciones IA para CSV de Dieta (Gym Tracker) — v2

## Propósito
Generar un archivo CSV **listo para importar** que siga **exactamente** la estructura de `plan_diet_template.csv` (inamovible).

## Insumos obligatorios
1) `plan_diet_template.csv`  
2) Este documento (`PLAN_CSV_AI_INSTRUCTIONS_DIET.md`)

## Contrato de salida (estricto)
- Cuando produzcas el entregable final: **responde SOLO con CSV crudo** (sin Markdown, sin texto extra).
- La **primera línea** debe ser la cabecera oficial **exacta** y en el **mismo orden**.
- No renombres columnas, no reordenes, no agregues columnas, no agregues comentarios.
- Separador: coma. Codificación: UTF-8.

## Cabecera oficial (inamovible)
log_date,calories_target_kcal,protein_target_g,carbs_target_g,fat_target_g,breakfast,snack_1,lunch,snack_2,dinner,notes

## Reglas por columna
- `log_date`: formato `AAAA-MM-DD`.
- `calories_target_kcal`: entero (kcal/día). Vacío si no hay base suficiente.
- `protein_target_g`, `carbs_target_g`, `fat_target_g`: enteros (g/día). Vacío si no hay base suficiente.
- `breakfast`, `snack_1`, `lunch`, `snack_2`, `dinner`: texto simple (sin saltos de línea). Vacío si `write_meals="no"`.
- `notes`: texto simple (sin saltos de línea). Úsalo para aclaraciones operativas (p. ej., “ajustar sal/agua”, “día social”, “hidratación”).

## Flujo estándar (multi‑turn)
1) **Recibir objetivos y contexto** del usuario.
2) Si falta información crítica para fijar calorías/macros o para redactar comidas: emitir **bloque `<missing_critical_data>`** y detener la generación.
3) Tras recibir las respuestas en el formato pedido: generar el CSV final.

### Preguntas críticas mínimas (formato de respuesta obligatorio)
Usa **máximo 5 preguntas**. Cada pregunta pide un objeto JSON para minimizar fricción.

1) Rango de fechas del plan (incluye ambos)  
Formato esperado: `{"start_date":"AAAA-MM-DD","end_date":"AAAA-MM-DD"}`

2) Datos base y actividad (sin decimales en altura)  
Formato esperado: `{"age_years":N,"sex":{"A":"hombre","B":"mujer","C":"otro"},"height_cm":N,"weight_kg":N,"activity_outside_gym":{"A":"baja","B":"media","C":"alta"}}`

3) Objetivo cuantificable y horizonte  
Formato esperado: `{"weight_trend":"bajar|mantener|subir","target_weight_kg":N}`

4) Restricciones y preferencias dietarias  
Formato esperado: `{"diet_type":{"A":"omnivoro","B":"pescetariano","C":"vegetariano","D":"vegano"},"allergies_or_intolerances":["..."],"avoid":["..."],"meals_per_day":{3|4|5}}`

5) Contenido del CSV (comidas escritas)  
Formato esperado: `{"write_meals":{"A":"si","B":"no"}}`

### Definición operativa de `write_meals`
- `write_meals="si"`: rellenar `breakfast/snack_1/lunch/snack_2/dinner` con propuestas concretas.
- `write_meals="no"`: dejar **vacías** esas columnas y completar solo calorías/macros + `notes`.

## Reglas de consistencia (nutrición)
- No inventes datos médicos. Si el usuario reporta condiciones clínicas relevantes, prioriza seguridad y deja campos vacíos si no hay base.
- Mantén `protein_target_g`, `carbs_target_g`, `fat_target_g` coherentes con `calories_target_kcal` (4 kcal/g proteína y carbos; 9 kcal/g grasa).
- Si el objetivo es “bajar” y el horizonte es corto, evita déficits extremos: si no puedes justificar un número con los datos del usuario, deja `calories_target_kcal` vacío y explica en `notes` qué faltó.

## Construcción de comidas (solo si `write_meals="si"`)
- Texto breve por comida, sin saltos de línea.
- Respetar `diet_type`, `avoid` y alergias/intolerancias.
- Incluir proteína en cada comida principal.
- Usar “notes” para recomendaciones operativas (hidratación, fibra, timing simple).

## Validación final (obligatoria antes de entregar)
- Cabecera exacta y orden exacto.
- 1 fila por día desde `start_date` hasta `end_date` (incluye ambos).
- Fechas válidas y consecutivas (sin saltos).
- CSV parseable (coma, UTF‑8).
- Cero texto fuera del CSV.
