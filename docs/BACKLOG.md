# BACKLOG

Ultima actualizacion: 2026-02-25
Objetivo: backlog unico de trabajo prospectivo (post-v1).
Estado release: v1.0.0.0 cerrada.
Fuente de consolidacion: resultados QA desktop v3 + mejoras post-v1 unificadas en este documento.

## 1) Cierre v1.0.0.0 (completado)

- Todos los items de cierre `BQA-001` a `BQA-023` quedaron en estado `Hecho`.
- QA desktop v3 final: `97 OK`, `3 PENDIENTE (no bloqueantes)`, `5 N/A`.
- No quedan pendientes bloqueantes para la linea v1.

## 2) Roadmap Post-v1 (unificado)

| Enhancement ID | Origen | Oportunidad | Impacto esperado | Propuesta | Criterio de salida | Estado |
|---|---|---|---|---|---|---|
| PEV2-001 | Backlog pre-QA (13.3) | La vista `Planes` depende de importacion CSV manual para arrancar en usuarios nuevos. | Menos friccion de onboarding y menor dependencia de soporte tecnico. | Evolucionar `Planes` a catalogo guiado: asistente inicial + catalogo base configurable para generar dieta/entreno desde GUI y persistirlo en tablas de plan. | Un usuario nuevo puede crear un plan minimo completo sin editar ni importar CSV. | Pendiente |
| PEV2-002 | DSK-026 (OK con nota) | Se permite crear check-in minimo con muy pocos campos. | Riesgo de distorsion en metricas y analitica al mezclar registros incompletos. | Definir politica de completitud minima (campos obligatorios o score de calidad de registro) y aplicarla en create/update. | No se guardan registros que incumplan la regla de completitud definida, o se guardan marcados con calidad insuficiente sin contaminar calculos agregados. | Pendiente |
| PEV2-003 | DSK-033 (OK con nota) | Persisten inconsistencias percibidas en formato de miles para `pasos` segun contexto. | Menor confianza visual en datos numericos. | Unificar formato local de miles en todos los componentes (tabla, filtros, resumenes, tooltips y export visible). | `pasos` se presenta con formato consistente en toda la UI. | Pendiente |
| PEV2-004 | DSK-056 (OK con nota) | La accion `Limpiar` para volver a estado nulo se percibe poco natural. | Friccion UX en un control de uso frecuente. | Reemplazar copy `Limpiar` por `—` (o iconografia equivalente) en los selectores SI/NO/null. | El estado nulo es entendible y consistente sin texto confuso. | Pendiente |
| PEV2-005 | DSK-076 (PENDIENTE no bloqueante) | Falta validar en QA real casos de importacion de entreno con archivos malformados. | Riesgo de regresiones silenciosas en feedback de errores CSV. | Añadir fixtures negativos oficiales + caso QA reproducible + test automatizado de import estricto. | El sistema demuestra y documenta respuestas correctas ante al menos 3 escenarios invalidos representativos. | Pendiente |
| PEV2-006 | DSK-093 (OK con nota) | `Ver fotos` deberia inhabilitarse cuando no hay fotos disponibles. | Evita clics muertos y mejora affordance UX. | Deshabilitar/ocultar CTA de galeria hasta tener al menos una foto de progreso cargada. | El boton solo aparece habilitado cuando existe contenido fotografico. | Pendiente |
| PEV2-007 | DSK-097 (OK con nota) | El export de check-ins descargaba como `diet.csv`. | Naming tecnico incorrecto para el usuario final. | Renombrar archivo de exportacion a `check-ins.csv` y mantener alias legacy `/export/diet.csv` para compatibilidad. | La descarga refleja el dominio correcto en nombre de archivo y copy de UI. | Hecho |
| PEV2-008 | DSK-101 (OK con nota) | `Enviar mail` en reporte de bug no esta condicionado a destino configurado. | Posible accion sin efecto o error evitable. | Habilitar CTA solo si existe destinatario configurado; si no, mostrar alternativa clara (copiar diagnostico). | No hay intentos de envio sin configuracion valida. | Pendiente |
| PEV2-009 | DSK-100 y DSK-102 (PENDIENTE) | Flujo backup/restore no se probo de punta a punta en QA manual final. | Riesgo operativo en escenarios de recuperacion de datos. | Ejecutar bateria de pruebas controladas de backup/restore (exito, archivo invalido, confirmaciones, rollback visual) y validar capa de toasts sobre overlay/modal. | Flujo de backup queda verificado con evidencia reproducible y mensajes legibles en todas las capas de UI. | Pendiente |
| PEV2-010 | DSK-103 (N/A) | Falta validacion completa de coherencia de `/help` para escenario multiusuario. | Riesgo de deuda documental/UX en rollout amplio. | Revisar y alinear `/help` con header/footer, navegacion y estado actual de features. | `/help` pasa matriz dedicada y queda consistente con la app principal. | Pendiente |
| PEV2-011 | DSK-080, DSK-081, DSK-095, DSK-096 (N/A) | La matriz QA desktop contiene casos obsoletos por cambios de arquitectura de vistas. | Ruido en QA y menor trazabilidad de resultados. | Publicar matriz QA desktop siguiente version sin casos deprecados y con cobertura movida a su vista actual. | La nueva matriz elimina N/A estructurales y mejora cobertura real por modulo. | Pendiente |

## 3) Notas de gobernanza

- Este archivo pasa a ser la unica fuente de backlog prospectivo.
- El historial de trabajo previo se conserva en el historial de Git (commits/tags), sin carpetas de historico dentro de `docs/`.
