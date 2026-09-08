# Gurobean Engine — protocolo de evidencia del juego real

## Propósito

Este protocolo define cómo convertir una sesión real de Gurobean Coffee en evidencia reproducible para R5–R8. La existencia de un ajuste estadístico, una simulación o una ejecución sintética **no** constituye evidencia del juego.

## Unidad de observación

Cada observación debe conservar, como mínimo:

- `round_number`: 5, 6, 7 u 8.
- `source`: `game`, `game_capture` o `game_observation`.
- `variables`: decisiones/estado observado antes de la respuesta.
- `outputs`: respuesta observada del juego.
- `repetitions`: número de repeticiones bajo las mismas condiciones.
- captura o referencia de captura cuando exista.
- fecha/hora y un identificador único de observación en el artefacto externo de captura.

### R5 — markup → arrivals

Registrar `markup` y `arrival_rate` observados en condiciones comparables. Cubrir el dominio de markup y no concentrar todas las observaciones en un único punto.

### R6 — congestion → balking

Registrar `queue` o `wait_minutes`, además de `stay_probability`. Cuando sea posible registrar conteos `successes` y `trials` para el ajuste binomial-logístico.

### R7 — multi-cup orders

Registrar las condiciones de demanda y `order_size` por cliente/pedido. Conservar suficientes observaciones para distinguir la distribución de tamaños y no sólo su media.

### R8 — service rate → cost

Registrar `service_rate` y `barista_cost_per_hour`. Cubrir el rango operativo de velocidad y conservar el costo realmente observado.

## Diseño experimental mínimo

Para cada ronda:

1. Usar al menos 8 condiciones independientes antes de considerar promoción.
2. Cubrir el dominio operativo, incluyendo puntos bajos, medios y altos.
3. Repetir condiciones relevantes para separar ruido de señal.
4. Mantener constantes las variables que no sean parte de la respuesta estudiada cuando el juego lo permita.
5. Registrar la captura original y una tabla estructurada derivada de ella.
6. No sustituir una observación faltante por un valor inferido.

## Validación

La promoción debe pasar, en este orden:

1. Provenance válida (`game`, `game_capture` o `game_observation`).
2. Ronda única y válida.
3. Validación numérica y de dominio.
4. Ajuste de familias candidatas con restricciones de monotonía cuando corresponda.
5. Métrica de error de entrenamiento.
6. Validación out-of-sample determinista sobre un holdout no usado para ajustar el modelo.
7. Diagnóstico de residuos y revisión de monotonía/dominio.
8. Parámetros congelados en un artefacto reproducible.
9. Regression tests para el evaluador promovido.
10. Sólo después, uso de esos parámetros para recomendaciones del motor.

## Regla de integridad

Nunca convertir automáticamente datos sintéticos, demo, datos generados por el propio simulador o valores estimados desde una figura en `source=game`. La procedencia es una propiedad de la evidencia y no una etiqueta decorativa.

## Artefacto recomendado

Guardar una captura estructurada por ronda, por ejemplo:

```json
{
  "round_number": 5,
  "source": "game_capture",
  "capture_id": "R5-001",
  "variables": {"markup": 1.0},
  "outputs": {"arrival_rate": 35.7},
  "repetitions": 3,
  "notes": "Condición observada en juego real"
}
```

Los valores anteriores son sólo la forma del registro; no son datos reales y no deben incorporarse como evidencia.

## Resultado esperado

El resultado final de calibración debe permitir responder tres preguntas por separado:

- **¿Qué observó el juego?** — evidencia primaria.
- **¿Qué modelo reproduce esas observaciones?** — calibración/validación.
- **¿Qué decisión recomienda el motor?** — optimización sobre el modelo ya validado.

Nunca mezclar esas tres capas en un único número o etiqueta de "PASS".
