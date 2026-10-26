# Ruta austral SYD→SCL frente a la geodésica

Ejecución `runs/syd_scl_austral_v2` (configuración `config/syd_scl_austral.yaml`): 27 vuelos con
CARI-7, mismos perfiles, fechas y convenciones que `runs/matrix_v1`. Todas las cifras son **dosis
efectiva ICRP 103**. Solo fondo galáctico (GCR) con promedio mensual.

```bash
uv run airrad run --config config/syd_scl_austral.yaml --run-id syd_scl_austral_v2
uv run airrad report runs/syd_scl_austral_v2
```

## Origen de la ruta austral

Las rutas oceánicas de LATAM entre Oceanía y Santiago suelen ir bastante más al sur que el círculo
máximo. Para cuantificar el efecto se digitalizó la traza de una captura de Flightradar24 (vuelo
rotulado LA809, sentido SYD→SCL, fecha desconocida). Los detalles están en
`data/tracks/SYD-SCL_fr24_LA809_digitized.provenance.json`:

- **Calibración.** Proyección Web Mercator calibrada con los dos aeropuertos. Se comprobó de forma
  independiente con la línea del ecuador (1.5 px de diferencia) y con el meridiano de 180° (cae en el
  límite FIR). La precisión es de ≈ ±0.2–0.3° en el tramo austral.
- **Puntos.** 79 waypoints horizontales, sin tiempos ni altitudes. La trayectoria llega a
  **72.1° S** (frente a 61.8° S de la geodésica) y es un **5.3 % más larga** (11 963 km frente a 11 363 km).
- **Tramo estimado.** El tramo más austral (≈ 140° W–165° W) está punteado en Flightradar24: es una
  posición estimada sin cobertura ADS-B.
- **Representatividad.** Es un solo vuelo. Las rutas oceánicas se planifican cada día (vientos, ETOPS,
  etc.), así que esta no representa a todos los vuelos. Que la desviación se deba al viento es
  plausible, pero aquí no se verifica.
- **Etiqueta.** La trayectoria se presenta como "Trayectoria sintética por waypoints aproximados; no
  representa necesariamente la ruta operacional".
- **Sentido.** Solo se calcula SYD→SCL, que es el sentido observado. La ruta en sentido contrario se
  planifica con otros vientos.

## Resultados

**Dosis por tramo SYD→SCL (`gs470`: misma velocidad media respecto al suelo, así que la ruta austral
dura 825 min frente a 783):**

| Perfil | Fecha | Geodésica | Ruta austral | Diferencia por tramo | Diferencia por hora |
|---|---|---|---|---|---|
| FL330 | 2020‑02 | 53.8 µSv | 59.5 µSv | +10.7 % | +5.0 % |
| FL330 | 2024‑10 | 36.2 µSv | 39.2 µSv | +8.2 % | +2.7 % |
| FL370 | 2020‑02 | 72.0 µSv | 80.0 µSv | +11.0 % | +5.4 % |
| FL370 | 2024‑10 | 47.7 µSv | 51.8 µSv | +8.5 % | +2.9 % |
| FL370 | 2026‑08 | 57.3 µSv | 62.7 µSv | +9.4 % | +3.8 % |
| FL410 | 2020‑02 | 91.1 µSv | 101.7 µSv | +11.6 % | +5.9 % |
| FL410 | 2024‑10 | 59.1 µSv | 64.3 µSv | +8.8 % | +3.2 % |

FL330 y FL410 también se calcularon para 2026‑08 (+9.1 % y +9.8 %); están en
`report/comparisons.csv`.

**Misma duración (`igual_tiempo`: ambas en 783 min).** Representa el caso en que el viento de cola
compensa la mayor longitud. A FL370 la ruta austral da +5.2 % (2020‑02), +2.7 % (2024‑10) y +3.6 %
(2026‑08). Es el efecto de la latitud por sí sola.

En resumen, con `gs470` la diferencia de ≈ +11 % (FL370, 2020‑02) se reparte en partes casi iguales:
un 5.4 % por la mayor duración y un 5.4 % por la mayor tasa media.

## Proyección anual (aproximación)

Para armar rotaciones, `syd_scl_austral_v2` añade a la `v1` el tramo de ida SCL→SYD por la geodésica
(bloque `ida_geodesica`: FL370, `gs470`, 783 min, tres fechas). Los 24 vuelos de la `v1` salen
idénticos en la `v2`. No hay traza observada de la ida, así que no se supone que vaya por el sur.

Una rotación es una ida SCL→SYD por la geodésica más una vuelta SYD→SCL, por la geodésica o por la
ruta austral. Cada tramo usa la dosis de su sentido (FL370, `gs470`):

| Dosis por rotación | 2020‑02 | 2024‑10 | 2026‑08 |
|---|---|---|---|
| Vuelta geodésica (72.0 + 72.0 µSv en 2020‑02) | 144.0 µSv | 95.4 µSv | 114.5 µSv |
| Vuelta austral | 151.9 µSv | 99.5 µSv | 119.9 µSv |
| Diferencia | +5.5 % | +4.2 % | +4.7 % |

**Dosis efectiva anual en 12 meses (mSv)**, repitiendo la misma condición solar todo el año:

| Rotaciones/mes | Horas en el aire/año (geodésica / austral) | 2020‑02 geod. / austral | 2024‑10 geod. / austral | 2026‑08 geod. / austral |
|---|---|---|---|---|
| 1 | 313 / 322 | 1.73 / 1.82 | 1.15 / 1.19 | 1.37 / 1.44 |
| 2 | 626 / 643 | 3.46 / 3.65 | 2.29 / 2.39 | 2.75 / 2.88 |
| 3 | 940 / 965 | 5.18 / 5.47 | 3.44 / 3.58 | 4.12 / 4.32 |
| 4 | 1253 / 1286 | 6.91 / 7.29 | 4.58 / 4.77 | 5.50 / 5.76 |

- Es una **aproximación**: no simula la condición solar de cada vuelo. Un año real queda entre las
  columnas según la modulación de cada mes. Las fechas solo acotan el rango del modelo.
- Los calendarios son hipotéticos. No se afirma que cumplan límites laborales u operacionales, y
  4 rotaciones al mes suman unas 1 250–1 290 h en el aire.
- La diferencia anual entre ambas variantes es la de una rotación (+4 % a +6 %): un solo vuelo
  digitalizado, sin tiempos ni altitudes reales.
- Las cifras están en `runs/syd_scl_austral_v2/report/annual_calendars.csv` y la figura en
  `report/figures/exposicion_anual.png`.

## Por qué ir 10° más al sur añade relativamente poco

En el modelo, la tasa **se satura** a alta latitud geomagnética. En ese sector, por encima de
≈ 58–60° S el corte geomagnético deja de limitar y la tasa queda en una meseta:

| FL370, `gs470` | 2020‑02 | 2024‑10 |
|---|---|---|
| Tasa máxima, geodésica (≈ 58° S) | 7.27 µSv/h | 4.39 µSv/h |
| Tasa a más de 70° S, ruta austral | 7.27 µSv/h | 4.39 µSv/h |
| Minutos de crucero a ≥ 98 % de la tasa máxima: geodésica / austral | 260 / 411 | 337 / 457 |

La ruta austral no alcanza tasas más altas. Lo que hace es pasar unos 150 min más en la meseta. El
efecto es mayor en 2020‑02 (baja modulación solar) que en 2024‑10, igual que la sensibilidad a la
latitud en las otras rutas.

La latitud geográfica no basta para predecir la tasa. Entre 55° S y 60° S, la ruta austral (cerca
de 150° E, al sur de Tasmania) tiene 6.17 µSv/h, y la geodésica (cerca de 170° W) 6.46 µSv/h. CARI
la calcula con rigideces de corte (rejilla IGRF2010), no con la latitud.

## Validación

- 27/27 comprobaciones ok:
  - Σ tasa·Δt coincide con la dosis de CARI con |Δ| ≤ 4.7×10⁻⁵.
  - Posición evaluada por CARI a ≤ 7 m de la trayectoria, incluido el cruce de ±180°.
  - Profundidad atmosférica en los nodos de la tabla coincidente hasta 1.5×10⁻⁶.
- Los vuelos geodésicos SYD→SCL de esta ejecución coinciden exactamente (tasa, posición y dosis
  acumulada en cada minuto) con los de `runs/matrix_v1`, calculados con el modo de ejecución anterior.

## Limitaciones específicas

- Un solo vuelo, digitalizado de una imagen. El tramo más austral es una estimación de FR24.
- No hay altitudes ni tiempos reales: se usan los perfiles y duraciones supuestos del estudio.
- Para cuantificar la variabilidad real habría que importar varias trayectorias ADS-B reales
  (`imported_tracks`, con altitud de presión) de distintas fechas y en ambos sentidos.
- Aplican las limitaciones generales de `docs/supuestos_limitaciones.md`: campo IGRF2010 congelado,
  promedio mensual, sin SPE y sin blindaje del fuselaje.
