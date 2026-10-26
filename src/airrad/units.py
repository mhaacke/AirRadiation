"""Unit conversions and altitude conventions.

Altitude conventions used in this project
-----------------------------------------
* ``pressure_altitude``: altitude in the ICAO Standard Atmosphere (ISA) that
  corresponds to the measured static pressure. A flight level is pressure
  altitude in hundreds of feet (FL370 = 37 000 ft pressure altitude).
* ``geopotential``: geopotential altitude. In the ISA / U.S. Standard
  Atmosphere 1976 (identical below 32 km), pressure is tabulated as a function
  of geopotential altitude, so pressure altitude == geopotential altitude *of
  the standard atmosphere*.
* ``geometric_msl``: geometric height above mean sea level.

CARI-7 reads altitudes in feet and converts them to atmospheric depth
(g/cm^2) with ``ATMOSPHERE/FT-GM.DAT`` (routine ``FT2GPCMS`` in
``SKY_LIBS_7.FOR``), documented in the source as "geopotential altitude in
feet" from the U.S. Standard Atmosphere 1976. A flight level therefore maps to
the CARI input without numerical conversion: FL x 100 ft.
"""

from __future__ import annotations

import numpy as np

FT_TO_M = 0.3048  # exact, international foot
M_TO_FT = 1.0 / FT_TO_M
USV_PER_MSV = 1000.0
# Effective Earth radius used by the U.S. Standard Atmosphere 1976 for the
# geometric <-> geopotential relation.
R_EARTH_USSA76_M = 6_356_766.0


def ft_to_m(ft):
    return np.asarray(ft, dtype=float) * FT_TO_M


def m_to_ft(m):
    return np.asarray(m, dtype=float) * M_TO_FT


def usv_to_msv(usv):
    return np.asarray(usv, dtype=float) / USV_PER_MSV


def msv_to_usv(msv):
    return np.asarray(msv, dtype=float) * USV_PER_MSV


def flight_level_to_ft(fl):
    """Flight level -> pressure altitude in feet (FL370 -> 37000 ft)."""
    return np.asarray(fl, dtype=float) * 100.0


def geometric_to_geopotential_m(z_m):
    """Geometric height -> geopotential altitude (USSA-1976 relation)."""
    z = np.asarray(z_m, dtype=float)
    return R_EARTH_USSA76_M * z / (R_EARTH_USSA76_M + z)


def geopotential_to_geometric_m(h_m):
    h = np.asarray(h_m, dtype=float)
    return R_EARTH_USSA76_M * h / (R_EARTH_USSA76_M - h)


ALTITUDE_UNITS = {"ft": 1.0, "m": M_TO_FT}
ALTITUDE_REFERENCES = ("pressure_altitude", "geopotential", "geometric_msl")


def to_cari_altitude_ft(values, unit: str, reference: str) -> tuple[np.ndarray, list[str]]:
    """Convert altitudes to the convention CARI-7 expects.

    Returns the altitude in feet as standard-atmosphere geopotential altitude
    (equivalently ISA pressure altitude) and a list of warnings describing any
    approximation made.
    """
    if unit not in ALTITUDE_UNITS:
        raise ValueError(f"Unidad de altitud no soportada: {unit!r}; use 'ft' o 'm'")
    if reference not in ALTITUDE_REFERENCES:
        raise ValueError(
            f"Referencia de altitud no soportada: {reference!r}; use una de {ALTITUDE_REFERENCES}. "
            "Altura elipsoidal GNSS no se acepta sin un modelo de geoide."
        )
    ft = np.asarray(values, dtype=float) * ALTITUDE_UNITS[unit]
    warnings: list[str] = []
    if reference == "pressure_altitude":
        return ft, warnings
    if reference == "geopotential":
        warnings.append(
            "Altitud geopotencial pasada sin cambios a CARI: CARI asume la Atmósfera "
            "Estándar EE.UU. 1976 para convertirla en profundidad atmosférica."
        )
        return ft, warnings
    # geometric_msl
    h_m = geometric_to_geopotential_m(ft * FT_TO_M)
    warnings.append(
        "Altura geométrica convertida a geopotencial (USSA-1976). La profundidad "
        "atmosférica resultante supone atmósfera estándar; la altitud de presión real "
        "puede diferir en cientos de metros."
    )
    return h_m * M_TO_FT, warnings
