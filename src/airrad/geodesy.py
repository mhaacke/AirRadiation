"""WGS84 geodesics and antimeridian handling (pyproj / GeographicLib)."""

from __future__ import annotations

import numpy as np
from pyproj import Geod

WGS84 = Geod(ellps="WGS84")


def normalize_lon(lon):
    """Wrap longitudes to [-180, 180)."""
    return (np.asarray(lon, dtype=float) + 180.0) % 360.0 - 180.0


def unwrap_lon(lon):
    """Make a longitude sequence continuous (no ±360° jumps), e.g. for plotting."""
    lon = np.asarray(lon, dtype=float)
    return np.rad2deg(np.unwrap(np.deg2rad(lon)))


def inverse(lat1, lon1, lat2, lon2) -> tuple[float, float, float]:
    """Forward azimuth, back azimuth (deg) and geodesic distance (m)."""
    az12, az21, dist = WGS84.inv(lon1, lat1, lon2, lat2)
    return float(az12), float(az21), float(dist)


def points_along_geodesic(lat1, lon1, lat2, lon2, distances_m) -> tuple[np.ndarray, np.ndarray]:
    """Points at given distances from (lat1, lon1) along the geodesic to (lat2, lon2)."""
    az12, _, _ = inverse(lat1, lon1, lat2, lon2)
    d = np.asarray(distances_m, dtype=float)
    lons, lats, _ = WGS84.fwd(np.full_like(d, lon1), np.full_like(d, lat1), np.full_like(d, az12), d)
    return np.asarray(lats), normalize_lon(lons)


def segment_distances_m(lats, lons) -> np.ndarray:
    """Geodesic length of each consecutive segment of a polyline."""
    lats = np.asarray(lats, dtype=float)
    lons = np.asarray(lons, dtype=float)
    if len(lats) < 2:
        return np.zeros(0)
    _, _, d = WGS84.inv(lons[:-1], lats[:-1], lons[1:], lats[1:])
    return np.asarray(d)


def points_along_polyline(lats, lons, distances_m) -> tuple[np.ndarray, np.ndarray]:
    """Points at given distances along a polyline whose segments are geodesics."""
    lats = np.asarray(lats, dtype=float)
    lons = np.asarray(lons, dtype=float)
    cum = np.concatenate([[0.0], np.cumsum(segment_distances_m(lats, lons))])
    out_lat, out_lon = [], []
    for d in np.asarray(distances_m, dtype=float):
        j = int(np.clip(np.searchsorted(cum, d, side="right") - 1, 0, len(cum) - 2))
        la, lo = interpolate_on_segment(lats[j], lons[j], lats[j + 1], lons[j + 1], (d - cum[j]) / (cum[j + 1] - cum[j]))
        out_lat.append(la)
        out_lon.append(lo)
    return np.array(out_lat), normalize_lon(out_lon)


def interpolate_on_segment(lat1, lon1, lat2, lon2, fraction) -> tuple[float, float]:
    """Point at a fraction of the geodesic between two points."""
    az12, _, dist = inverse(lat1, lon1, lat2, lon2)
    lon, lat, _ = WGS84.fwd(lon1, lat1, az12, dist * fraction)
    return float(lat), float(normalize_lon(lon))


def crosses_antimeridian(lons) -> bool:
    """True if consecutive points jump across ±180° (short-way crossing)."""
    lon = np.asarray(lons, dtype=float)
    return bool(np.any(np.abs(np.diff(lon)) > 180.0))
