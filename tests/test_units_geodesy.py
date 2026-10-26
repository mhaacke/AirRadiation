import numpy as np
import pytest

from airrad import geodesy, units


def test_feet_metres_exact():
    assert units.ft_to_m(1.0) == pytest.approx(0.3048, abs=0)
    assert units.ft_to_m(37000) == pytest.approx(11277.6)
    assert units.m_to_ft(units.ft_to_m(41000.0)) == pytest.approx(41000.0, rel=1e-15)


def test_usv_msv():
    assert units.usv_to_msv(1000.0) == pytest.approx(1.0)
    assert units.usv_to_msv(74.621) == pytest.approx(0.074621)
    assert units.msv_to_usv(units.usv_to_msv(123.4)) == pytest.approx(123.4)


def test_flight_level_is_pressure_altitude_ft():
    assert units.flight_level_to_ft(370) == 37000.0


def test_geometric_geopotential_round_trip_and_magnitude():
    z = np.array([0.0, 11277.6, 20000.0])
    h = units.geometric_to_geopotential_m(z)
    assert h[0] == 0.0
    assert z[1] - h[1] == pytest.approx(20.0, abs=0.5)  # ~20 m at FL370
    assert units.geopotential_to_geometric_m(h) == pytest.approx(z)


def test_cari_altitude_requires_explicit_unit_and_reference():
    with pytest.raises(ValueError):
        units.to_cari_altitude_ft([1000], "feet", "pressure_altitude")
    with pytest.raises(ValueError):
        units.to_cari_altitude_ft([1000], "m", "ellipsoidal")
    ft, w = units.to_cari_altitude_ft([37000], "ft", "pressure_altitude")
    assert ft[0] == 37000 and w == []
    ft, w = units.to_cari_altitude_ft([11277.6], "m", "geometric_msl")
    assert ft[0] < 37000 and w  # converted to geopotential, with a warning


def test_normalize_and_unwrap_longitude():
    assert geodesy.normalize_lon([180.0, 190.0, -181.0]).tolist() == [-180.0, -170.0, 179.0]
    lon = np.array([178.0, 179.5, -179.5, -178.0])
    assert geodesy.crosses_antimeridian(lon)
    un = geodesy.unwrap_lon(lon)
    assert np.all(np.abs(np.diff(un)) < 2.0)
    assert un[-1] == pytest.approx(182.0)


def test_geodesic_points_reach_destination_and_cross_antimeridian():
    scl = (-33.393, -70.786)
    mel = (-37.6707, 144.8379)
    _, _, d = geodesy.inverse(*scl, *mel)
    lat, lon = geodesy.points_along_geodesic(*scl, *mel, np.linspace(0, d, 200))
    assert lat[-1] == pytest.approx(mel[0], abs=1e-9)
    assert lon[-1] == pytest.approx(mel[1], abs=1e-9)
    assert geodesy.crosses_antimeridian(lon)
    assert geodesy.segment_distances_m(lat, lon).sum() == pytest.approx(d, rel=1e-9)
