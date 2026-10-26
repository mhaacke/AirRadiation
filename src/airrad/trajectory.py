"""Trajectories: synthetic WGS84 geodesics and CSV import."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
import pandas as pd

from . import geodesy
from .airports import Airport
from .profiles import AltitudeProfile
from .units import ALTITUDE_REFERENCES, ALTITUDE_UNITS, to_cari_altitude_ft

SYNTHETIC_LABEL = "Trayectoria geodésica sintética; no representa necesariamente la ruta operacional"
VIA_LABEL = "Trayectoria sintética por waypoints aproximados; no representa necesariamente la ruta operacional"
CSV_COLUMNS = ("timestamp_utc", "latitude_deg", "longitude_deg", "altitude")


@dataclass
class Trajectory:
    """Time-ordered 4-D track.

    ``points`` columns: t_min (minutes since first point), timestamp_utc,
    lat, lon ([-180, 180)), lon_unwrapped, alt_ft (in ``altitude_reference``),
    cum_dist_km and, for synthetic tracks, phase.
    """

    points: pd.DataFrame
    altitude_reference: str
    synthetic: bool
    label: str
    meta: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def duration_min(self) -> float:
        return float(self.points["t_min"].iloc[-1] - self.points["t_min"].iloc[0])

    @property
    def has_integer_minutes(self) -> bool:
        t = self.points["t_min"].to_numpy(dtype=float)
        return bool(np.allclose(t, np.round(t)))

    @property
    def total_distance_km(self) -> float:
        return float(self.points["cum_dist_km"].iloc[-1])

    def southernmost(self) -> dict:
        i = self.points["lat"].idxmin()
        p = self.points.loc[i]
        return {"lat": float(p.lat), "lon": float(p.lon), "t_min": float(p.t_min)}

    def cari_altitude_ft(self) -> tuple[np.ndarray, list[str]]:
        return to_cari_altitude_ft(self.points["alt_ft"].to_numpy(), "ft", self.altitude_reference)

    def resample_minutes(self, step_min: int = 1) -> "Trajectory":
        """Resample onto whole-minute times (needed for CARI-7 DEG waypoints).

        Horizontal interpolation follows the geodesic between bracketing
        points; altitude is linear in time.
        """
        t = self.points["t_min"].to_numpy(dtype=float)
        t_end = np.floor(t[-1])
        grid = np.arange(0.0, t_end + 0.5, step_min, dtype=float)
        if grid[-1] != t_end:
            grid = np.append(grid, t_end)
        lat, lon = [], []
        for tg in grid:
            j = int(np.clip(np.searchsorted(t, tg, side="right") - 1, 0, len(t) - 2))
            frac = (tg - t[j]) / (t[j + 1] - t[j])
            p0, p1 = self.points.iloc[j], self.points.iloc[j + 1]
            la, lo = geodesy.interpolate_on_segment(p0.lat, p0.lon, p1.lat, p1.lon, frac)
            lat.append(la)
            lon.append(lo)
        alt = np.interp(grid, t, self.points["alt_ft"].to_numpy())
        ts0 = self.points["timestamp_utc"].iloc[0]
        new = _build_points(grid, ts0, np.array(lat), np.array(lon), alt)
        w = list(self.warnings)
        if t[-1] - t_end > 1e-9:
            w.append(f"Remuestreo: se descartan {t[-1] - t_end:.2f} min finales (CARI usa minutos enteros).")
        return replace(self, points=new, warnings=w, meta={**self.meta, "resampled_step_min": step_min})


def _build_points(t_min, ts0, lat, lon, alt_ft, phase=None) -> pd.DataFrame:
    seg = geodesy.segment_distances_m(lat, lon)
    df = pd.DataFrame(
        {
            "t_min": np.asarray(t_min, dtype=float),
            "timestamp_utc": ts0 + pd.to_timedelta(np.asarray(t_min, dtype=float), unit="min"),
            "lat": np.asarray(lat, dtype=float),
            "lon": geodesy.normalize_lon(lon),
            "lon_unwrapped": geodesy.unwrap_lon(geodesy.normalize_lon(lon)),
            "alt_ft": np.asarray(alt_ft, dtype=float),
            "cum_dist_km": np.concatenate([[0.0], np.cumsum(seg)]) / 1000.0,
        }
    )
    if phase is not None:
        df["phase"] = phase
    return df


def synthesize_geodesic(
    origin: Airport,
    dest: Airport,
    profile: AltitudeProfile,
    airborne_min: int,
    departure_utc: pd.Timestamp,
    sample_min: float = 5.0,
    via: list[tuple[float, float]] | None = None,
) -> Trajectory:
    """Synthetic flight along the WGS84 geodesic between two airports.

    With ``via`` (intermediate (lat, lon) waypoints in flight order) the path is
    the polyline origin -> via -> destination, each segment a geodesic.

    Assumptions (labelled): constant ground speed = path length / airborne time;
    altitude piecewise linear between profile breakpoints; the regular
    sampling grid is merged with the profile breakpoints so that the profile
    is represented exactly by linear interpolation between waypoints.
    """
    if sample_min <= 0:
        raise ValueError("sample_min debe ser > 0")
    departure_utc = pd.Timestamp(departure_utc)
    if departure_utc.tzinfo is None:
        raise ValueError("departure_utc debe incluir zona horaria (UTC)")
    departure_utc = departure_utc.tz_convert("UTC")
    knots_t, knots_alt, warnings = profile.breakpoints(airborne_min, origin.elevation_ft, dest.elevation_ft)
    T = float(airborne_min)
    grid = np.arange(0.0, T, sample_min)
    t = np.unique(np.concatenate([grid, knots_t, [T]]))
    if not np.allclose(t, np.round(t)):
        warnings.append("Muestreo no entero: CARI-7 requiere minutos enteros; los tiempos se redondean.")
        t = np.unique(np.round(t))
    _, _, geod_m = geodesy.inverse(origin.lat, origin.lon, dest.lat, dest.lon)
    if via:
        vlat = [origin.lat, *(p[0] for p in via), dest.lat]
        vlon = [origin.lon, *(p[1] for p in via), dest.lon]
        dist_m = float(geodesy.segment_distances_m(vlat, vlon).sum())
        lat, lon = geodesy.points_along_polyline(vlat, vlon, dist_m * t / T)
    else:
        dist_m = geod_m
        lat, lon = geodesy.points_along_geodesic(origin.lat, origin.lon, dest.lat, dest.lon, dist_m * t / T)
    lat[-1], lon[-1] = dest.lat, geodesy.normalize_lon(dest.lon)
    alt = np.interp(t, knots_t, knots_alt)
    toc, tod = knots_t[1], knots_t[-2]
    phase = np.where(t <= toc, "ascenso", np.where(t >= tod, "descenso", "crucero"))
    pts = _build_points(t, departure_utc, lat, lon, alt, phase)
    meta = {
        "origin": origin.icao,
        "destination": dest.icao,
        "profile": profile.name,
        "airborne_min": int(airborne_min),
        "departure_utc": departure_utc.isoformat(),
        "sample_min": sample_min,
        "geodesic_distance_km": geod_m / 1000.0,
        "path_distance_km": dist_m / 1000.0,
        "n_via_waypoints": len(via or []),
        "ground_speed_kt": dist_m / 1852.0 / (T / 60.0),
        "profile_knots_min": knots_t.tolist(),
        "profile_knots_alt_ft": knots_alt.tolist(),
        "assumptions": [
            "Velocidad respecto al suelo constante a lo largo del tramo (supuesto).",
            "Altitud lineal por tramos entre quiebres del perfil (supuesto).",
            "Elevación del aeródromo tomada como altitud de presión ISA en origen/destino.",
        ],
    }
    return Trajectory(pts, "pressure_altitude", True, VIA_LABEL if via else SYNTHETIC_LABEL, meta, warnings)


def import_csv(
    path: str | Path,
    altitude_unit: str,
    altitude_reference: str,
    label: str | None = None,
    synthetic: bool = False,
) -> Trajectory:
    """Import a track CSV with columns timestamp_utc, latitude_deg, longitude_deg, altitude.

    ``altitude_unit`` ('ft'|'m') and ``altitude_reference``
    ('pressure_altitude'|'geopotential'|'geometric_msl') are mandatory: the
    file itself does not say what its altitude means.
    """
    if altitude_unit not in ALTITUDE_UNITS:
        raise ValueError(f"altitude_unit obligatorio y válido ('ft'|'m'), recibido {altitude_unit!r}")
    if altitude_reference not in ALTITUDE_REFERENCES:
        raise ValueError(f"altitude_reference obligatorio, uno de {ALTITUDE_REFERENCES}; recibido {altitude_reference!r}")
    df = pd.read_csv(path)
    missing = [c for c in CSV_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas en {path}: {missing}")
    ts = pd.to_datetime(df["timestamp_utc"], utc=True)
    if ts.isna().any():
        raise ValueError("timestamp_utc contiene valores no interpretables")
    if not ts.is_monotonic_increasing or ts.duplicated().any():
        raise ValueError("timestamp_utc debe ser estrictamente creciente")
    lat = df["latitude_deg"].to_numpy(dtype=float)
    lon = df["longitude_deg"].to_numpy(dtype=float)
    if np.any(np.abs(lat) > 90) or np.any(np.abs(lon) > 180):
        raise ValueError("Latitud/longitud fuera de rango")
    alt_ft = df["altitude"].to_numpy(dtype=float) * ALTITUDE_UNITS[altitude_unit]
    t_min = (ts - ts.iloc[0]).dt.total_seconds().to_numpy() / 60.0
    pts = _build_points(t_min, ts.iloc[0], lat, lon, alt_ft)
    meta = {"source_file": str(path), "altitude_unit_in": altitude_unit, "n_points": len(df)}
    return Trajectory(pts, altitude_reference, synthetic, label or f"Trayectoria importada de {Path(path).name}", meta)
