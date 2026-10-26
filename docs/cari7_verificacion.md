# CARI-7: verificación de capacidades, formatos y condiciones de uso

Verificado el 2026-10-25 contra la página oficial, el paquete descargado y su código fuente.
Cada afirmación indica su fuente. Nada aquí se infirió sin comprobarlo.

| Fuente | Referencia |
|---|---|
| Página oficial | <https://www.faa.gov/data_research/research/med_humanfacs/aeromedical/radiobiology/cari7> (actualizada el 2026-09-28) |
| Paquete | `cari_7exe.zip`, SHA-256 `a20d9ca8aec142337be52632fbe6f251545d771bdfc0e6bbb69e7a4ddfc94197` |
| Guía de usuario | Copeland K., *CARI Documentation: User's Guide*, DOT/FAA/AM-21/6, marzo 2021 (`202106.pdf`) |
| Transporte atmosférico | DOT/FAA/AM-21/5 (`202105.pdf`) |
| Rigidez de corte | DOT/FAA/AM-19/4 (`201904.pdf`) |
| Código fuente incluido | `src/cari7.f`, `SKY_LIBS_7.FOR`, `GEODESIC.FOR` (Fortran 95) |

## 1. Disponibilidad en Linux y arquitectura

- El paquete trae `cari-7_linux_intel_exe`, idéntico a `Linux_Intel_64bit/cari-7(v4_1_3_linux_intel)`:
  **ELF 64-bit x86-64**, enlazado dinámicamente con glibc y compilado con GCC 4.1.2 (RHEL 5).
  SHA-256 `adc60bf82bff4ab6832cb8eb2ee2d0e11967cbe0b81eac54ccf8ecb23a78019b`.
- **No hay binario ARM64.** En este equipo (macOS ARM64) se ejecuta en un contenedor
  `linux/amd64` (`debian:bookworm-slim` fijado por digest) dentro de la VM de Colima.
  Se probaron dos traductores x86-64, qemu-user y Rosetta (`colima start --vz-rosetta`). Con ambos,
  `EXAMPLE.DEG` sale idéntico a la referencia, y el `.DAT` completo de SCL→MEL FL370 2020‑02
  (780 pasos) es **idéntico byte a byte** entre ambos. Rosetta es unas 1.9 veces más rápido
  (99 s frente a 186 s en ese vuelo). La matriz `runs/matrix_v1` se ejecutó con Rosetta.
- Discrepancia de versión, registrada sin resolver: el nombre del archivo y el fuente indican 4.1.3
  (14‑abr‑2021, una corrección de nombres de archivo de salida en Linux), pero el binario
  incrusta el banner `June 24, 2020 (4.1.2)`.
- `Linux_Intel_64bit/readme.txt` todavía dice que durante el teletrabajo por COVID-19 no habría
  ejecutables Linux; aun así, el binario está presente y funciona.

## 2. Ejecución por lotes, sin interacción

Fuentes: Guía de usuario §"Control files" y §"Avoiding the Menus"; `GETINI` y `RUNDEG` en `cari7.f`.

- `CARI.INI`: formato `A10,A2,A12` hasta `END`. Solo se comparan los **dos primeros caracteres** de
  cada clave. `MENUS = NO!` activa el modo por lotes y `OS = UNIX` activa las rutas POSIX.
  - Una línea `DIAGNOSE` asigna en realidad `DISPLAY` (ambas empiezan por `DI`), así que no la escribimos.
  - CARI-7 **fuerza** `GCR=4`, `SP=0` y `NVRC='0'`, sea cual sea el INI.
- `DEFAULT.INP`: solo se leen 5 líneas: (1) fecha `yyyy/mm/dd` o `0000/00/00` para usar la del
  archivo, (2) hora, (3) partícula (0 = total), (4) magnitud (*tally*) y (5) archivo.
- Con `*.DEG`, CARI ejecuta `ls -1 *.DEG > FILELIST.TXT` mediante `CALL SYSTEM`, así que la imagen
  necesita `/bin/sh` y `ls`. Cada `X.DEG` produce `X.SUM` y `X.DAT`.
- Con `*.DEG`, **todos** los `.DEG` del directorio se procesan en orden alfabético, y la fecha del primer
  archivo se arrastra a los siguientes. Un experimento con `EXAMPLE.DEG` (01/2002) presente en el
  directorio dio 3.9613 µSv en lugar de 4.7257 µSv para un vuelo de 02/2020, y el `.SUM` declaraba
  `DATE: 2002/01/00`. Por eso cada lote agrupa una sola fecha, el directorio de trabajo nunca contiene
  la raíz de la instalación y el adaptador verifica en cada `.SUM` que la fecha usada sea la pedida.
- Durante la ejecución, CARI **escribe** en `AIRPORTS/` (índices), `DIAGNOSE/`,
  `GCR_MODELS/ISO_GCR2.OUT` y el directorio de trabajo (`fort.40`, `DEBUGGER.DAT`, `FILELIST.TXT`).
  Por eso cada lote corre en su propio directorio, con copias de esos subdirectorios y enlaces de
  solo lectura a `SHOWERS/`, `FORBUSH/`, `CUTOFFS/` y `KP_INDEX/`.

- **Rendimiento.** CARI hace muchas lecturas y escrituras pequeñas. Con el directorio de trabajo en la
  carpeta compartida de Colima (virtiofs), la VM quedaba un 75 % ociosa y cada proceso usaba un
  10–30 % de un núcleo. El runner docker copia por defecto `AIRPORTS ATMOSPHERE DIAGNOSE GCR_MODELS
  SOLARMOD CUTOFFS FORBUSH KP_INDEX SHOWERS` y las entradas del lote a `/tmp/cari_run` dentro del
  contenedor, ejecuta allí y devuelve `*.SUM`, `*.DAT`, `FILELIST.TXT`, `fort.40`, `DEBUGGER.DAT` e
  `ISO_GCR2.OUT` (`docker_local_copy`). Un vuelo de 150 min pasó de 40 s a 4 s. Comprobado idéntico
  byte a byte con `EXAMPLE.DEG` y con los 132 archivos de salida de la matriz SCL–PUQ recalculada.

## 3. Trayectorias por waypoints (`.DEG`) y altitud

Fuentes: Guía §"Flights along a user-specified path"; `DEG_FLT_DOSE` en `cari7.f`; `FT2GPCMS` en `SKY_LIBS_7.FOR`.

- Línea 1: `MM/YYYY, nombre`, que implica promedio mensual (día = 00). Línea 2: cabecera.
  Luego, una línea por waypoint: `grados, minutos, N/S, grados, minutos, E/W, pies, minuto`.
- Algoritmo: un paso por minuto, evaluado en el **punto medio** del minuto; posición por
  geodésica entre waypoints (NGS FORWARD/INVERSE sobre GRS80: a = 6378137 m, f = 1/298.257222101) y
  altitud lineal en el tiempo. La dosis del vuelo es `Σ tasa/60`.
- Límites: duración ≤ 2000 min, ≤ 2000 waypoints y altitud ≤ 300 000 ft. El primer waypoint debe
  estar en el minuto 0, porque la integración empieza en el minuto 1.
- **Altitud:** los pies se convierten en profundidad atmosférica (g/cm²) mediante `ATMOSPHERE/FT-GM.DAT`.
  El fuente documenta esa conversión como "geopotential altitude in feet" de la **U.S. Standard Atmosphere 1976**.
  La altitud de presión ISA (nivel de vuelo × 100 ft) es, por definición, la altitud geopotencial de
  la atmósfera estándar que tiene esa presión, así que **FL370 se pasa como 37 000 ft sin
  conversión**. Comprobación de extremo a extremo: CARI reporta 220.891 g/cm² en crucero a FL370,
  igual que la fila de 37.00 kft de `FT-GM.DAT`.
- Una altura geométrica (por ejemplo, GNSS sobre el nivel del mar) no es altitud de presión.
  El importador CSV exige declarar la referencia; `geometric_msl` se convierte a geopotencial
  (USSA-76) y genera una advertencia. Altura elipsoidal: rechazada.

## 4. Magnitudes y unidades

Fuentes: Guía §"Tally Options" y Tabla 2; `DKSTR` en `cari7.f`.

| tally | magnitud | unidad (dosis / tasa) |
|---|---|---|
| 2 | Dosis efectiva, ICRP 103 | µSv / µSv h⁻¹ |
| 3 | Dosis efectiva, ICRP 60 | µSv / µSv h⁻¹ |
| 4 | Equivalente de dosis ambiental H*(10) | µSv / µSv h⁻¹ |
| 5 | Dosis absorbida promedio en cuerpo entero | µGy / µGy h⁻¹ |
| 1, 6–8 | fluencia, Si 0.5/0.3 mm, NM-64 | no usadas |

- `.SUM`: dosis total del vuelo. `.DAT`: por paso, latitud, longitud (0–360° E), profundidad,
  paso, **tasa** y dosis **acumulada**. La regla Σ tasa/60 = acumulada se verificó en el ejemplo oficial.
- En archivos `.ANS` (ubicaciones), este binario rotula la tasa como `microSv` en vez de
  `microSv/hr` y omite la columna SIGMA del ejemplo de referencia. Los valores numéricos coinciden
  exactamente con la referencia. Este proyecto no usa `.ANS`.
- Incertidumbre declarada en `HELP.TXT`: "about 30% for commercial altitudes", tras aplicar un factor
  de seguridad de 2. Es una cifra global del modelo, no un intervalo de confianza por escenario.

## 5. Datos solares y geomagnéticos; fechas soportadas

- Modulación: LIS ISO 2004 modulado por **potencial heliocéntrico mensual**
  (`SOLARMOD/MV-DATES.L99`, de 1958 hasta **08/2026** en este paquete). `MORDATES.2K` tiene prioridad
  y contiene entradas de prueba (`2012/12/12`, `00/4500`, `12/2112`); evitamos esas fechas.
  Si falta el mes pedido, CARI usa el potencial más reciente disponible, y la guía advierte que esa
  aproximación se degrada a más de 2 meses de distancia.
- Forbush (`FORBUSH/FORBUSH.DAT`) y Kp (`KP_INDEX/KP_INDEX.TXT`) llegan hasta 2026-08-31. Solo se
  aplican cuando se pide un día y una hora concretos. **Con promedio mensual (día = 00) no se usan.**
- Rigidez de corte: rejillas de 1965, 1980, 1990, 1995, 2000 y 2010, interpoladas linealmente en el
  tiempo. **Desde 2010 se usa la de IGRF2010 sin extrapolar** (`FINDCUT`, `CASE DEFAULT`). Para 2020
  y 2024 no se representa la variación secular del campo posterior a 2010.
- Los SPE no se incluyen. CARI-7A tiene espectros SPE (feb‑1956, sep‑1989) y espectros de usuario,
  pero quedan fuera del MVP.

## 6. ¿Hace falta CARI-7A?

No para el MVP. Lo que pide el estudio (dosis efectiva/H*(10)/absorbida de GCR por waypoints con
promedio mensual) está en CARI-7. CARI-7A solo agregaría otros modelos de GCR (BO11/BO14), SPE,
superposición, cortes no verticales y blindaje del vehículo, y según la página oficial corre
"several hundred times slower". El adaptador está separado del análisis
(`airrad.engines.base.DoseEngine`) para incorporarlo después.

## 7. Condiciones de uso y redistribución

- `HELP.TXT` y la guía: "disseminated under the sponsorship of the U.S. Department of Transportation
  in the interest of information exchange. The United States Government assumes no liability".
- `src/SRC_NOTES.TXT`: los códigos del autor "may be freely distributed" con reconocimiento. Hay
  partes de terceros (NGS FORWARD/INVERSE y una rutina de spline).
- No se encontró una licencia explícita para redistribuir **binarios ni datos**. Por prudencia,
  este repositorio **no** los incluye: `scripts/install_cari7.py` los descarga de la FAA y verifica su hash.

## 8. Verificación de la instalación

Los tres ejemplos oficiales se ejecutaron en el contenedor amd64:

| ejemplo | resultado |
|---|---|
| `EXAMPLE.DEG` (01/2002) | `.SUM` y `.DAT` **idénticos byte a byte** a la referencia: 0.50704 µSv |
| `EXAMPLES.LOC` (114 ubicaciones) | 114 valores **idénticos**; difieren solo los rótulos (sección 4) |
| `EXAMPLE.BIG` (KJFK–TJSJ, 03/1995) | 9.3274 µSv frente a 9.2704 µSv de referencia (+0.6 %). `Examples/README.txt` advierte que pueden no coincidir exactamente con el ejecutable y los datos actuales. No usamos el modo BIG. |

`uv run airrad check` repite la verificación del ejemplo DEG y guarda el resultado en `validation/official_example/`.
