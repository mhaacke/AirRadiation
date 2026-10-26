# Análisis Santiago–Punta Arenas (SCL–PUQ)

Ejecución `runs/scl_puq_v1` (configuración `config/scl_puq.yaml`): 32 vuelos calculados con CARI-7,
con el mismo paquete FAA, contenedor y convenciones que `runs/matrix_v1`. Todas las cifras son **dosis
efectiva ICRP 103** sobre una **trayectoria geodésica sintética que no representa necesariamente la
ruta operacional**, salvo que se indique otra magnitud. Solo fondo galáctico (GCR), promedio mensual.

Reproducir:

```bash
uv run airrad run --config config/scl_puq.yaml --run-id scl_puq_v1
uv run airrad report runs/scl_puq_v1
```

## Supuestos específicos de esta ruta

| Supuesto | Valor | Comentario |
|---|---|---|
| Aeródromos | SCEL (−33.39°, 1555 ft) y SCCI (−53.00°, 139 ft) | OurAirports, dominio público |
| Trayectoria | geodésica WGS84, 2179 km, casi meridiana (~70.8° W) | la latitud más austral es el propio PUQ |
| Duración `gs470` | 150 min | igual criterio que el estudio transpacífico, para que sean comparables; no es un horario ni un tiempo real en el aire |
| Duración `gs400` | 176 min | sensibilidad elegida a mano |
| Perfiles | FL330, FL370 (idénticos a `study.yaml`) y FL390 (ascenso 34 min, descenso 33 min) | FL390 es una cota superior hipotética para un fuselaje angosto |
| Fechas | 2020‑02 (254 MV), 2024‑10 (1040 MV) y 2026‑08 (642 MV) | 2026‑08 es el último mes del paquete instalado, no una predicción |

## Resultados (FL370, `gs470`, media de ambos sentidos)

| Fecha | Dosis por tramo | Tasa media del tramo | Tasa media en crucero | Tasa máxima |
|---|---|---|---|---|
| 2020‑02 | 5.89 µSv | 2.36 µSv/h | 3.30 µSv/h | 3.74 µSv/h |
| 2024‑10 | 4.89 µSv | 1.96 µSv/h | 2.75 µSv/h | 3.01 µSv/h |
| 2026‑08 | 5.35 µSv | 2.14 µSv/h | 3.00 µSv/h | 3.34 µSv/h |

- **La tasa crece hacia el sur.** En crucero a FL370 (2020‑02) pasa de 2.96 µSv/h a 37.4° S a
  3.70 µSv/h a 48.8° S, un 25 % más. En 2024‑10 la subida es de 2.52 a 2.99 µSv/h. El máximo se da al
  final del crucero, justo antes del descenso a PUQ.
- **Ascenso y descenso pesan mucho en un tramo corto.** Ocupan 62 de 150 min (41 %), pero aportan
  1.04 de 5.88 µSv (18 %). Por eso la tasa media del tramo queda bastante por debajo de la de crucero.

**Variación entre escenarios** (diferencias entre supuestos, **no** incertidumbre del modelo):

| Factor variado (referencia) | Diferencia por tramo | Por hora de vuelo |
|---|---|---|
| Fecha 2024‑10 frente a 2020‑02 | −14.0 % a −17.5 % | igual |
| Fecha 2026‑08 frente a 2020‑02 | −7.5 % a −9.4 % | igual |
| FL330 frente a FL370 | −19.1 % a −19.6 % | igual |
| FL390 frente a FL370 | +7.4 % a +8.1 % | igual (en crucero: +11 %; el ascenso más largo supuesto le quita tiempo de crucero) |
| Duración `gs400` frente a `gs470` | +24.5 % a +24.6 % | +6.1 % a +6.2 % (más fracción del tramo en crucero) |
| Sentido (PUQ→SCL frente a SCL→PUQ) | −0.2 % a +1.1 % | — viene de las entradas: el ascenso (30 min) y el descenso (32 min) caen en extremos distintos, y las elevaciones de los aeródromos difieren |
| Paso de muestreo 2 y 1 min frente a 5 min | 0 % | CARI integra internamente a 1 min |

**Otras magnitudes (SCL→PUQ, FL370, `gs470`).** Son magnitudes distintas; no se intercambian.

| Fecha | E (ICRP 103) | H*(10) | Dosis absorbida, cuerpo entero | H*(10)/E |
|---|---|---|---|---|
| 2020‑02 | 5.88 µSv | 6.49 µSv | 3.13 µGy | 1.10 |
| 2024‑10 | 4.88 µSv | 5.36 µSv | 2.70 µGy | 1.10 |
| 2026‑08 | 5.34 µSv | 5.88 µSv | 2.90 µGy | 1.10 |

## Comparación con las rutas transpacíficas (`runs/matrix_v1`)

Es comparable porque usa el mismo motor y los mismos datos, FL370 con el mismo ascenso y descenso,
`gs470` y las mismas dos fechas. Es una comparación **dentro del modelo**, no con mediciones.

| Ruta | Tiempo en el aire | Latitud más austral | Dosis por tramo 2020‑02 / 2024‑10 | Tasa media del tramo 2020‑02 / 2024‑10 | Tasa media en crucero 2020‑02 / 2024‑10 |
|---|---|---|---|---|---|
| SCL–PUQ | 2.5 h | 53.0° S | 5.9 / 4.9 µSv | 2.36 / 1.96 µSv/h | 3.30 / 2.75 µSv/h |
| SCL–AKL | 11.1 h | 52.6° S | 49.8 / 36.3 µSv | 4.48 / 3.27 µSv/h | 4.84 / 3.52 µSv/h |
| SCL–SYD | 13.1 h | 61.8° S | 72.0 / 47.7 µSv | 5.52 / 3.66 µSv/h | 5.91 / 3.90 µSv/h |
| SCL–MEL | 13.0 h | 66.9° S | 74.7 / 48.5 µSv | 5.74 / 3.73 µSv/h | 6.14 / 3.97 µSv/h |

- Un tramo SCL–PUQ da entre un 8 % y un 10 % de la dosis de un tramo SCL–MEL, y entre un 12 % y un 13 %
  de uno SCL–AKL (2020‑02 y 2024‑10, respectivamente).
  La diferencia viene sobre todo de la duración.
- Por hora de vuelo, SCL–PUQ también queda por debajo, por dos razones. Primero, la fracción de ascenso
  y descenso es mayor (41 % del tramo, frente a ≈ 8 % en SCL–MEL). Segundo, el crucero transcurre entre
  37° S y 49° S, mientras que las rutas transpacíficas pasan horas en latitudes más altas. SCL–AKL alcanza
  casi la misma latitud máxima (52.6° S), pero cruza el Pacífico Sur en otra región geomagnética, así que
  la latitud geográfica sola no determina la tasa: CARI la calcula con rigideces de corte (rejilla IGRF2010).
- El efecto de la fecha es menor en SCL–PUQ (−14 % a −17 % de 2020‑02 a 2024‑10) que en las rutas
  transpacíficas (−26 % a −37 %). En el modelo, la modulación solar pesa menos donde el corte
  geomagnético es mayor.

## Calendarios anuales hipotéticos (aproximación)

Se repite la dosis representativa (FL370, `gs470`, media de ambos sentidos). No se simula cada vuelo
y no se afirma que los calendarios cumplan límites laborales u operacionales.

| Tramos al mes | Horas al año | 2020‑02 | 2024‑10 | 2026‑08 |
|---|---|---|---|---|
| 10 | 300 h | 0.71 mSv | 0.59 mSv | 0.64 mSv |
| 20 | 600 h | 1.41 mSv | 1.17 mSv | 1.28 mSv |
| 30 | 900 h | 2.12 mSv | 1.76 mSv | 1.93 mSv |

Con unas 900 h al año, el calendario mixto transpacífico de `matrix_v1` (892 h) da 4.7 / 3.2 mSv
(2020‑02 / 2024‑10). La programación doméstica SCL–PUQ da 2.1 / 1.8 mSv, aproximadamente la mitad,
con las mismas horas.

## Validación

- 32/32 comprobaciones ok (`runs/scl_puq_v1/report/validation_summary.json`):
  - Σ tasa·Δt reproduce la dosis de CARI con |Δ| ≤ 9.5×10⁻⁶.
  - La posición evaluada por CARI está a ≤ 7 m de la geodésica.
  - La profundidad atmosférica en los nodos de la tabla coincide hasta 2.5×10⁻⁶.
- Convergencia: 5, 2 y 1 min dan 5.8798 µSv.

## Limitaciones específicas

- La ruta real SCL–PUQ puede desviarse de la geodésica (aerovías, vientos del oeste en altura,
  alternativas). Con la tasa creciendo hacia el sur, el tiempo pasado al sur de 45° S es lo que más
  importa. Las trayectorias ADS-B pueden importarse con `imported_tracks`.
- Las duraciones `gs470` y `gs400` son supuestos. El tiempo en el aire real de un vuelo comercial no se
  deriva de horarios.
- Aplican las limitaciones generales de `docs/supuestos_limitaciones.md`: campo IGRF2010 congelado
  (relevante sobre Sudamérica), promedio mensual, sin SPE y sin blindaje del fuselaje.
