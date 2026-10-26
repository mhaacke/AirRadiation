# Handoff

Estado del proyecto al 2026-10-25. Para el detalle de métodos y resultados, ver el `README.md` y
`docs/`. Este archivo resume lo necesario para retomar el trabajo.

## Qué es

Estudio de escenarios reproducible de la dosis por radiación cósmica galáctica (GCR) en rutas
australes desde Santiago, con **CARI-7 (FAA)** como único motor. Todas las dosis provienen de CARI;
el código solo genera trayectorias, prepara entradas, lee salidas, valida y resume.

Reglas del proyecto que conviene respetar:

- **Nada de fórmulas propias de dosis.** Tampoco multiplicadores por la Anomalía del Atlántico Sur,
  por "ruta polar" ni por latitud.
- **No mezclar magnitudes** (dosis efectiva, H*(10), dosis absorbida) **ni integrar dos veces**
  valores que ya son dosis.
- **No inventar intervalos de confianza** ni convertir dosis en riesgo.
- **Anuales = aproximación.** Las extrapolaciones anuales se etiquetan como aproximación y no
  afirman cumplir límites laborales.
- **Etiquetar las trayectorias sintéticas**, tal como hace `trajectory.py`.
- **No redistribuir binarios ni datos de CARI** (ver `docs/cari7_verificacion.md` §7). Por eso
  `.gitignore` excluye `third_party/cari7/*` y la copia de `EXAMPLE.DEG` en `validation/`.

## Puesta en marcha en otra máquina

```bash
uv sync
uv run python scripts/install_cari7.py     # descarga CARI-7 de la FAA y verifica SHA-256
uv run airrad check                        # ejemplo oficial: debe dar "identical": true
uv run pytest -q                           # 29 pruebas (1 marcada "cari", requiere Docker)
```

**Requisitos de ejecución**

- CARI-7 es un binario Linux x86-64 y corre en Docker con `linux/amd64`.
- En macOS ARM se usó Colima con Rosetta: `colima start --vz-rosetta --cpu 10` (2 GiB de RAM bastan).
  Colima solo monta `$HOME`, así que el repositorio debe estar dentro de `$HOME`.

**Rendimiento**

- `engine.docker_local_copy: true` (por defecto) copia los datos de CARI al disco del contenedor.
  Sobre virtiofs era ~10× más lento.
- `max_parallel` en `config/*.yaml` es el número de contenedores simultáneos; usar ≈ número de vCPU.
- Con 10 vCPU, `matrix_v1` (66 vuelos) tarda ~2 min.

## Ejecuciones incluidas (`runs/`)

| Ejecución | Configuración | Vuelos | Qué responde | Documento |
|---|---|---|---|---|
| `matrix_v1` | `config/study.yaml` | 66 | SCL–MEL / SYD / AKL, ambos sentidos, perfiles, fechas, duraciones, magnitudes, calendarios | `README.md` |
| `scl_puq_v1` | `config/scl_puq.yaml` | 32 | Santiago–Punta Arenas | `docs/analisis_SCL-PUQ.md` |
| `syd_scl_austral_v2` | `config/syd_scl_austral.yaml` | 27 | SYD→SCL geodésica frente a la ruta austral digitalizada de FR24 (LA809), con calendarios de rotación | `docs/analisis_ruta_austral_SYD-SCL.md` |
| `syd_scl_austral_v1` | (versión anterior de la misma configuración) | 24 | igual que v2, sin la ida ni los calendarios; sus 24 vuelos son idénticos en v2 | — |

Las ejecuciones son inmutables: `airrad run` falla si el directorio existe. Para cambiar la matriz,
crear un `--run-id` nuevo. `airrad report <run>` regenera `report/` (CSV y figuras) sin llamar a CARI.

`runs/e2e_SCL-MEL` (prueba temprana con código anterior) está excluida de git y puede borrarse.

## Cómo regenerar todo

```bash
uv run airrad run --config config/study.yaml --run-id matrix_v1
uv run airrad report runs/matrix_v1
uv run python scripts/build_notebook.py runs/syd_scl_austral_v2   # o cualquier otra ejecución
```

El notebook (`notebooks/analisis_inicial.ipynb`) está ejecutado sobre `runs/syd_scl_austral_v2`.
`build_notebook.py` sirve para cualquier ejecución: lee todas las cifras de los archivos de la
ejecución y no tiene números escritos a mano.

## Pendientes y limitaciones conocidas

1. **Ruta austral = un solo vuelo**, digitalizado de una captura de FR24 sin tiempos ni altitudes; el
   tramo más austral es una estimación de FR24. Para cuantificar la variabilidad real hay que importar
   varias trazas ADS-B con altitud de presión, de distintas fechas y en ambos sentidos
   (`imported_tracks`; ver la sección "Trayectorias importadas" del README).
2. **Calendarios anuales.** Repiten la condición solar de un mes todo el año. Simular cada mes con su
   potencial (`docs/supuestos_limitaciones.md`, próximo paso 6) daría un año realista.
3. **Ida SCL→SYD.** Va siempre por la geodésica; no hay traza observada en ese sentido.
4. **Figura `acumulacion_anual.png` en `matrix_v1`.** Con 13 calendarios queda cargada; convendría
   filtrar calendarios o usar paneles.
5. **Fuera del alcance del MVP:** SPE/GLE, blindaje del fuselaje, campo geomagnético posterior a 2010
   (CARI-7 usa IGRF2010) y CARI-7A. Ver `docs/supuestos_limitaciones.md`.
6. **Bug encontrado y evitado:** si en el directorio de trabajo de CARI queda otro `.DEG`, su fecha se
   arrastra al vuelo siguiente. El adaptador copia solo los directorios de datos y las entradas del
   lote (`docs/cari7_verificacion.md` §2). No volver a copiar la raíz de la instalación.

## Mapa del código

| Módulo | Función |
|---|---|
| `src/airrad/trajectory.py` | Geodésica sintética, trayectoria por waypoints (`via`) e importación CSV. |
| `src/airrad/engines/cari7.py` | Escribe `.DEG` / `DEFAULT.INP`, ejecuta en Docker y lee `.SUM` / `.DAT`. |
| `src/airrad/pipeline.py` | Ejecución por lotes y manifiesto con hashes. |
| `src/airrad/scenarios.py` | Expande la matriz de escenarios. |
| `src/airrad/dosimetry.py` | Resúmenes y comparaciones. |
| `src/airrad/annual.py` | Calendarios, también por sentido: `"RUTA sentido"`. |
| `src/airrad/validation.py` | Comprueba Σ tasa·Δt frente a CARI, la posición y la profundidad atmosférica. |
| `src/airrad/plotting.py`, `src/airrad/report.py` | Figuras y CSV. El sentido de cada ruta se elige con `plotting.route_direction`. |
