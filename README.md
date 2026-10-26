# AirRadiation: exposición a radiación cósmica en rutas australes con CARI-7

Estudio de escenarios, reproducible y trazable, de la dosis por **radiación cósmica galáctica (GCR)**
en tripulaciones de las rutas Santiago–Melbourne, Santiago–Sídney y Santiago–Auckland (referencia),
en ambos sentidos. El motor de cálculo es **CARI-7** de la FAA. No hay ninguna fórmula empírica
propia: todas las dosis provienen de CARI.

> **No es una herramienta operacional.** Las trayectorias son geodésicas sintéticas y los perfiles,
> duraciones y calendarios son supuestos. Solo se considera el fondo galáctico: los eventos de
> partículas solares requieren un análisis específico posterior. Las dosis no se convierten en riesgos
> individuales.

## Contenido

| Ruta | Qué hay |
|---|---|
| `HANDOFF.md` | estado actual, puesta en marcha, ejecuciones incluidas y pendientes |
| `src/airrad/` | paquete: `trajectory` (generador e importador), `profiles`, `engines/cari7` (adaptador), `scenarios` (matriz), `pipeline` (lotes), `dosimetry`, `annual`, `validation`, `plotting`, `report`, `cli` |
| `config/study.yaml` | toda la configuración del estudio: rutas, perfiles, duraciones, fechas, matriz, calendarios |
| `config/scl_puq.yaml` | estudio complementario Santiago–Punta Arenas (ver `docs/analisis_SCL-PUQ.md`) |
| `config/syd_scl_austral.yaml` | SYD→SCL por la geodésica frente a una ruta austral digitalizada (ver `docs/analisis_ruta_austral_SYD-SCL.md`) |
| `data/tracks/` | waypoints aproximados digitalizados y su procedencia |
| `data/airports/` | coordenadas de aeropuertos (OurAirports, dominio público) y su procedencia |
| `scripts/` | `install_cari7.py`, `fetch_airports.py`, `build_notebook.py` |
| `runs/<run_id>/` | ejecución completa: configuración, trayectorias, entradas/salidas originales de CARI, manifiesto, `report/` (CSV y figuras) |
| `notebooks/analisis_inicial.ipynb` | notebook ejecutado con el análisis inicial |
| `docs/cari7_verificacion.md` | lo verificado sobre CARI-7 (formatos, unidades, datos, licencias) |
| `docs/supuestos_limitaciones.md` | supuestos, limitaciones y próximos pasos |
| `tests/` | pruebas; `tests/fixtures/` contiene solo datos **sintéticos** |

## Requisitos

- [uv](https://docs.astral.sh/uv/) y Python 3.13 (`uv` lo instala si falta).
- CARI-7 solo existe como binario **Linux x86-64** (y Windows). En otro host hace falta Docker con
  soporte `linux/amd64`. En macOS ARM64 con Colima, el directorio del proyecto debe estar bajo
  `$HOME` (Colima solo monta ese árbol). En Linux x86-64 se puede usar `runner: native` en `config/study.yaml`.

## Instalación y ejecución

```bash
uv sync                                         # dependencias exactas de uv.lock
uv run python scripts/install_cari7.py          # descarga CARI-7 de la FAA y verifica SHA-256
uv run airrad check                             # ejemplo oficial EXAMPLE.DEG: debe salir "identical": true
uv run pytest                                   # pruebas (incluye el ejemplo oficial si hay Docker)
uv run airrad scenarios                         # lista la matriz (66 escenarios)
uv run airrad run --run-id mi_ejecucion         # ejecuta la matriz con CARI-7
uv run airrad report runs/mi_ejecucion          # tablas, validaciones y figuras
uv run python scripts/build_notebook.py runs/mi_ejecucion
```

Opciones útiles: `airrad run --block convergencia`, `--contains SCL-MEL_out`, `--dry-run` (solo trayectorias).

**Rendimiento.** CARI lee y escribe muchos archivos pequeños. A través de la carpeta compartida
macOS↔VM (virtiofs), ese acceso dominaba el tiempo: los procesos usaban 10–30 % de un núcleo. Por eso
el runner docker copia por defecto los datos y las entradas al disco del contenedor, ejecuta allí y
devuelve las salidas (`docker_local_copy: true` en `engine`; `false` vuelve al modo anterior).
Resultados en VM Colima con Rosetta:

| Ejecución | Carpeta compartida, 4 vCPU | Disco del contenedor, 4 vCPU | Disco del contenedor, 10 vCPU |
|---|---|---|---|
| 1 vuelo SCL→PUQ, 150 min | 40 s | 4 s | — |
| Matriz SCL–PUQ, 32 vuelos | — | 34 s | — |
| Matriz ruta austral, 24 vuelos de ~13 h | — | 88 s | 56 s |
| Matriz `matrix_v1`, 66 vuelos | 42 min | — | 121 s |

Todos los modos dan resultados **idénticos byte a byte**:
- el ejemplo oficial;
- los 132 archivos `.SUM`/`.DAT`/`.DEG`/`ISO_GCR2.OUT` de `scl_puq_v1` recalculados;
- los 66 vuelos (49 290 pasos) de `matrix_v1` recalculados con 10 vCPU;
- la matriz austral con 4 y con 10 vCPU.

Configuración usada: `softwareupdate --install-rosetta --agree-to-license` y luego
`colima stop && colima start --vz-rosetta --cpu 10`, con `max_parallel: 10` en `config/*.yaml`. Con
otra cantidad de vCPU, iguala `max_parallel` a esa cantidad. Los resultados son idénticos con Rosetta
y con qemu.

**Paquete FAA actualizado.** La FAA reemplaza `cari_7exe.zip` cuando actualiza los datos mensuales.
Si el hash difiere del usado aquí, el instalador se detiene. Para continuar con el paquete nuevo:
`--accept-hash <sha>`. El hash instalado queda registrado en el manifiesto de cada ejecución.

## Trayectorias importadas

`config/study.yaml → imported_tracks` acepta CSV con `timestamp_utc, latitude_deg, longitude_deg,
altitude`. Es **obligatorio** declarar `altitude_unit` (`ft`|`m`) y `altitude_reference`
(`pressure_altitude`|`geopotential`|`geometric_msl`). La altura elipsoidal se rechaza. Las trayectorias
importadas se remuestrean a minutos enteros, como exige el formato DEG de CARI.

Una ruta también puede seguir waypoints horizontales intermedios (`routes.<id>.via: {path: CSV,
order: a_to_b|b_to_a}`, columnas `latitude_deg, longitude_deg`). Se unen por geodésicas y se aplican
los mismos perfiles y duraciones; la etiqueta es "Trayectoria sintética por waypoints aproximados; no
representa necesariamente la ruta operacional".

## Resultados de la ejecución `runs/matrix_v1`

66 vuelos calculados con CARI-7 (paquete FAA `a20d9ca8…`, binario `adc60bf8…`) en un contenedor
`linux/amd64` emulado con Rosetta. Las tablas completas están en `runs/matrix_v1/report/*.csv`, las
figuras en `runs/matrix_v1/report/figures/` y el análisis en `notebooks/analisis_inicial.ipynb`.
Todas las cifras son **dosis efectiva ICRP 103** sobre **trayectorias sintéticas**, salvo que se
indique otra magnitud.

**Dosis por tramo a FL370 (duración `gs470`, media de ambos sentidos)**

| Ruta | Latitud más austral | Tiempo en el aire | 2020‑02 (254 MV) | 2024‑10 (1040 MV) |
|---|---|---|---|---|
| SCL–MEL | 66.9° S | 13.0 h | 74.7 µSv (5.74 µSv/h) | 48.5 µSv (3.73 µSv/h) |
| SCL–SYD | 61.8° S | 13.1 h | 72.0 µSv (5.52 µSv/h) | 47.7 µSv (3.66 µSv/h) |
| SCL–AKL | 52.6° S | 11.1 h | 49.8 µSv (4.48 µSv/h) | 36.3 µSv (3.27 µSv/h) |

La tasa máxima a FL370 es 7.27 µSv/h en 2020‑02 y 4.39 µSv/h en 2024‑10 (rutas MEL/SYD).
Con FL410 llega a 9.42 µSv/h en 2020‑02.

**Variación entre escenarios.** Son diferencias entre supuestos definidos por el usuario; **no son
incertidumbre del modelo**.

| Factor variado (referencia) | Diferencia en la dosis por tramo |
|---|---|
| Fecha: 2024‑10 frente a 2020‑02 | −26 % a −37 % (en el modelo, mayor modulación solar → menos GCR) |
| Perfil: FL330 / FL410 frente a FL370 | −23 % a −26 % / +22 % a +27 % |
| Perfil escalonado FL330→390 frente a FL370 | −2 % a −10 % |
| Ruta: SCL–SYD frente a SCL–MEL | −1 % a −4 % |
| Ruta: SCL–AKL frente a SCL–MEL | −24 % a −35 % por tramo; −11 % a −24 % por hora de vuelo |
| Duración ±6.5 % (`asim_viento`) | ±6.4 % a ±7.0 % por tramo; ≤ 0.4 % por hora |
| Sentido, perfiles constantes | ≤ 0.3 % (solo cambian la elevación de los aeródromos y el ascenso/descenso) |
| Sentido, perfil escalonado | −4.5 % a −7.3 % a la vuelta. El nivel más alto (FL390) cae en el último cuarto del vuelo: a la ida queda cerca de Australia (alta latitud geomagnética) y a la vuelta, cerca de Chile. La diferencia sale de las entradas, no de una corrección |

**Otras magnitudes (SCL→MEL, FL370).** En 2020‑02: H*(10) = 85.6 µSv, E = 74.6 µSv y dosis absorbida
en cuerpo entero = 32.1 µGy. En 2024‑10: 54.4 µSv, 48.4 µSv y 23.4 µGy. Son magnitudes distintas y no
se intercambian; el cociente H*(10)/E es 1.12–1.15.

**Calendarios anuales hipotéticos (aproximación, FL370).** 2 a 8 tramos al mes durante 12 meses
dan 1.8–7.2 mSv (2020‑02) y 1.2–4.6 mSv (2024‑10) en SCL–MEL, con 312–1248 h de vuelo al año.
El calendario mixto (2 tramos al mes en cada ruta, 892 h al año) da 4.7 / 3.2 mSv. El cálculo repite
una dosis representativa, no simula cada vuelo y no afirma cumplir límites laborales.

**Validación** (`runs/matrix_v1/report/validation_*`)

- Ejemplo oficial `EXAMPLE.DEG` reproducido byte a byte (`uv run airrad check`).
- En los 66 vuelos:
  - Σ tasa·Δt reproduce la dosis de CARI con |Δ| ≤ 1.7×10⁻⁵ (la tasa se imprime con 5 cifras).
  - Tasa media temporal × duración = dosis.
  - Posición evaluada por CARI a ≤ 7 m de nuestra geodésica, también al cruzar ±180°.
  - Profundidad atmosférica en los nodos de la tabla de CARI coincidente hasta 2.5×10⁻⁶. Esto confirma
    de extremo a extremo que el nivel de vuelo se interpreta como altitud de presión ISA.
- Convergencia: muestreo de 5, 2 y 1 min → misma dosis (74.621 µSv). Es lo esperado, porque CARI
  integra internamente a 1 min sobre la geodésica entre waypoints.
- Resultados idénticos byte a byte con qemu y con Rosetta.
- No se contrastó con literatura: no se reunieron publicaciones en condiciones comparables (altitud,
  fecha, trayectoria y magnitud). Ver `docs/supuestos_limitaciones.md`.

## Ruta doméstica Santiago–Punta Arenas (`runs/scl_puq_v1`)

Estudio complementario con la misma metodología (`config/scl_puq.yaml`, 32 vuelos, 32/32 validaciones
ok). Análisis completo y comparación con las rutas transpacíficas en `docs/analisis_SCL-PUQ.md`.

| FL370, `gs470` (150 min), media de ambos sentidos | 2020‑02 | 2024‑10 | 2026‑08 |
|---|---|---|---|
| Dosis efectiva por tramo | 5.89 µSv | 4.89 µSv | 5.35 µSv |
| Tasa media del tramo / en crucero | 2.36 / 3.30 µSv/h | 1.96 / 2.75 µSv/h | 2.14 / 3.00 µSv/h |

## Ruta austral SYD→SCL (`runs/syd_scl_austral_v2`)

Las rutas de LATAM suelen ir bastante más al sur que el círculo máximo. Con una trayectoria
digitalizada de una captura de Flightradar24 (LA809, 72.1° S, un 5.3 % más larga; tramo austral
estimado por FR24), a FL370 la dosis SYD→SCL sube entre +8.5 % y +11.0 % por tramo frente a la
geodésica, a igual velocidad respecto al suelo. A igual duración sube entre +2.7 % y +5.2 %. Es poco
para 10° más de latitud porque, en el modelo, la tasa ya está saturada al sur de ≈ 58–60° S en ese
sector: la ruta austral no alcanza tasas mayores, sino que pasa unos 150 min más en la meseta.

Proyección anual (aproximación, ida SCL→SYD siempre por la geodésica): con 2 rotaciones al mes
(≈ 630–640 h en el aire) salen 3.46 / 2.29 / 2.75 mSv con vuelta geodésica y 3.65 / 2.39 / 2.88 mSv con
vuelta austral (2020‑02 / 2024‑10 / 2026‑08), entre un 4 % y un 6 % más. Detalles en
`docs/analisis_ruta_austral_SYD-SCL.md`.

Para limitaciones (campo geomagnético congelado en 2010 dentro de CARI-7, promedio mensual, sin SPE,
sin blindaje del fuselaje) y próximos pasos, ver `docs/supuestos_limitaciones.md`. Para lo verificado
sobre el motor, ver `docs/cari7_verificacion.md`.
