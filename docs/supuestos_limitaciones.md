# Supuestos, limitaciones y próximos pasos

## Alcance

- **Estudio de escenarios.** No reconstruye vuelos reales ni es una herramienta operacional certificada.
- **Solo radiación cósmica galáctica (GCR).** Los eventos de partículas solares (SPE/GLE) requieren un
  análisis específico posterior; CARI-7 no los modela.
- No se convierten dosis en probabilidades individuales de cáncer ni se emiten conclusiones clínicas.

## Supuestos de entrada (todos configurables en `config/study.yaml`)

| Supuesto | Valor en el ejemplo | Comentario |
|---|---|---|
| Trayectoria | geodésica WGS84 entre aeropuertos | etiquetada "Trayectoria geodésica sintética; no representa necesariamente la ruta operacional" |
| Trayectoria por waypoints (opcional) | geodésicas entre waypoints aproximados (p. ej., digitalizados de una imagen) | etiquetada "Trayectoria sintética por waypoints aproximados; no representa necesariamente la ruta operacional"; misma velocidad constante y perfil supuestos |
| Velocidad respecto al suelo | constante en todo el tramo | igual que el modo BIG de CARI |
| Duración `gs470` | distancia / 470 kt, igual en ambos sentidos | no es un horario comercial ni un tiempo real en el aire |
| Duración `asim_viento` | SCL→Oceanía más largo, regreso más corto (≈ ±6.5 %) | ilustrativo, elegido a mano, no derivado de datos meteorológicos |
| Perfiles constantes | FL330 / FL370 / FL410 con ascenso 25/30/38 min y descenso 30/32/35 min | FL410 es una cota superior hipotética |
| Perfil escalonado | FL330→350→370→390, ¼ del tiempo nivelado en cada nivel, 1000 ft/min | no es un perfil validado para un avión concreto |
| Altitud | altitud de presión ISA = FL × 100 ft | CARI la interpreta como altitud geopotencial USSA‑1976 (sin conversión) |
| Aeródromos | elevación del campo = altitud de presión en origen y destino | atmósfera estándar |
| Fechas | 2020‑02 (254 MV) y 2024‑10 (1040 MV) | justificadas por potencial heliocéntrico (CARI) y SILSO |
| Condiciones | promedio mensual | sin Forbush ni Kp horarios |
| Blindaje del avión | ninguno | práctica habitual; CARI-7 no lo modela |
| Hora de salida | día 15, 03:00 UTC | solo etiqueta los timestamps; no influye en la dosis con promedio mensual |

## Lo que deliberadamente **no** se hace

- No hay multiplicadores ad hoc por Anomalía del Atlántico Sur, proximidad al polo ni "ruta polar".
  El blindaje geomagnético lo representa CARI con rigideces de corte. La intensidad local del campo
  magnético no es la rigidez de corte.
- No se presupone que más actividad solar implique más fondo galáctico: el efecto lo calcula el modelo.
- No se inventan diferencias físicas entre sentidos. Con la misma trayectoria invertida y la misma duración,
  las diferencias residuales vienen solo de entradas distintas (elevación de los aeródromos y duración de
  ascenso/descenso en cada extremo).
- No hay intervalos de confianza. La cifra global de CARI (~30 % a altitudes comerciales, con factor de
  seguridad 2, `HELP.TXT`) describe el modelo, no la variación entre escenarios.

## Limitaciones del motor relevantes para estas rutas

- **Campo geomagnético congelado en 2010:** para 2020 y 2024 CARI-7 usa la rejilla IGRF2010. La deriva
  secular posterior (incluida la evolución de la región de bajo campo sobre Sudamérica y el Atlántico Sur)
  no se representa.
- Rigidez de corte efectiva vertical, ajustada por altitud y con flujo isótropo (NVCR = 0, forzado).
  Los cortes no verticales solo están en CARI-7A.
- Pasos de 1 minuto y waypoints en minutos enteros; duración ≤ 2000 min.
- Atmósfera estándar: la profundidad real a una altitud de presión dada coincide con la estándar por
  definición, pero una altura geométrica importada requiere el supuesto de atmósfera estándar.

## Extrapolación anual

La dosis anual = dosis representativa por tramo × número de tramos. Es una **aproximación**: no simula
las condiciones solares ni geomagnéticas de cada vuelo del año. Se presenta con ambas fechas como
cotas de escenario, no como intervalo. Un tramo es un vuelo de ida **o** de vuelta; una rotación son
dos tramos. No se afirma que estos calendarios cumplan límites laborales u operacionales.

## Próximos pasos sugeridos

1. Trayectorias reales (ADS-B/FDR) importadas por CSV, con altitud de presión explícita.
2. Fechas concretas con hora (activa Forbush y Kp en CARI) para vuelos reales.
3. Análisis específico de SPE/GLE (p. ej., CARI-7A con espectros de evento u otros modelos).
4. Sensibilidad a la rejilla de rigidez de corte post‑2010, con otro motor o con CARI-7A.
5. Contraste con literatura o mediciones solo en condiciones comparables (altitud, fecha, trayectoria y
   magnitud), sin ajustar factores.
6. Calendarios anuales que simulen cada mes con su propio potencial heliocéntrico, en lugar de repetir
   una dosis representativa.
