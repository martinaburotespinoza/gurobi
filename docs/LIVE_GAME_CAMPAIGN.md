# Gurobean — campaña real de observaciones

## Objetivo

Registrar observaciones del juego Gurobean para que R5–R8 puedan ser calibradas y validadas con evidencia real. Esta campaña **no sustituye** la certificación matemática R1–R4 ni convierte datos sintéticos en evidencia de juego.

## Punto de partida: R1

R1 comienza únicamente con café caliente y los datos entregados por el juego:

- Precio de venta: ₲4 por taza vendida.
- Frijoles utilizados: 10 g por taza preparada.
- Agua utilizada: 6 oz por taza preparada.
- Frijoles disponibles: 500 g/h.
- Agua disponible: 150 oz/h.
- Llegadas medias: 15 clientes/h.
- Capacidad media del barista: 25 clientes/h.

El motor debe conservar esta semántica: no introducir café frío ni variables de rondas posteriores dentro de R1.

## Flujo de campaña

1. Abrir la consola pública.
2. Seleccionar `Modo Juego` y comenzar en R1.
3. Ejecutar primero una prueba con los valores base sin alterar decisiones para comprobar que el flujo funciona.
4. En el juego real, registrar cada decisión y resultado observable en `/capture`.
5. Mantener el número de prueba creciente y conservar las condiciones de cada observación.
6. Repetir por ronda hasta disponer de datos suficientes para la relación específica que se quiera calibrar.
7. Exportar `gurobean_game_observations.json` al terminar la sesión.
8. Validar el conjunto antes de cualquier ajuste de parámetros.
9. Separar entrenamiento/calibración de validación fuera de muestra.
10. Solo promover parámetros a producción después de pasar el evidence gate.

## Procedencia permitida

Para calibración de producción se aceptan únicamente:

- `game`
- `game_capture`
- `game_observation`

No se acepta como evidencia de paridad de juego una observación sintética o generada por el propio simulador.

## R5–R8

- R5: markup → demanda.
- R6: congestión → balking/permanencia.
- R7: pedidos multi-taza.
- R8: tasa de servicio y costo de servicio.

Los coeficientes no deben inferirse arbitrariamente. Deben estimarse a partir de observaciones reales y después someterse a validación estadística, restricciones de dominio y prueba fuera de muestra.

## R9

R9 no es una ronda del juego. Es el release gate técnico para R1–R4 y requiere el entorno Gurobi/licencia correspondiente. La consola pública no intenta reproducir esa certificación local.

## Artefactos

La captura del navegador persiste temporalmente en `localStorage` y permite exportar JSON/CSV. El JSON exportado debe conservarse como evidencia de campaña y no modificarse manualmente después de la captura; si se corrige un dato, debe generarse una nueva versión trazable.
