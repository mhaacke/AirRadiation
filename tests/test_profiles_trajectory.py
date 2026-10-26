from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from airrad.airports import Airport
from airrad.geodesy import WGS84
from airrad.profiles import AltitudeProfile
from airrad.trajectory import SYNTHETIC_LABEL, VIA_LABEL, import_csv, synthesize_geodesic

FIX = Path(__file__).parent / "fixtures"
SCL = Airport("SCEL", "SCL", "Santiago", -33.393, -70.786, 1555)
MEL = Airport("YMML", "MEL", "Melbourne", -37.6707, 144.8379, 434)
DEP = pd.Timestamp("2020-02-15T03:00Z")


def constant(fl=370, climb=30, descent=32):
    return AltitudeProfile.from_config(f"FL{fl}", {"type": "constant", "cruise_fl": fl, "climb_min": climb, "descent_min": descent})


def step():
    return AltitudeProfile.from_config(
        "STEP",
        {"type": "step", "levels_fl": [330, 350, 370, 390], "cruise_fractions": [0.25] * 4,
         "step_climb_fpm": 1000, "climb_min": 25, "descent_min": 32},
    )  # fmt: skip


def test_constant_profile_knots():
    t, a, w = constant().breakpoints(780, 1555, 434)
    assert t.tolist() == [0, 30, 748, 780]
    assert a.tolist() == [1555, 37000, 37000, 434]
    assert w == []


def test_step_profile_time_budget():
    t, a, _ = step().breakpoints(780, 1555, 434)
    assert t[0] == 0 and t[-1] == 780 and t[-2] == 780 - 32
    assert np.all(np.diff(t) > 0)
    assert np.allclose(t, np.round(t))
    assert sorted(set(a[1:-1])) == [33000, 35000, 37000, 39000]
    # 3 step climbs of 2000 ft at 1000 ft/min = 6 min at most 0.5 min rounding each
    level_time = sum(t[i + 1] - t[i] for i in range(1, len(t) - 2) if a[i] == a[i + 1])
    assert level_time == pytest.approx(780 - 25 - 32 - 6, abs=2)


def test_profile_rejects_impossible_duration():
    with pytest.raises(ValueError):
        constant(climb=400, descent=400).breakpoints(780, 0, 0)
    with pytest.raises(ValueError):
        AltitudeProfile.from_config("x", {"type": "step", "levels_fl": [330, 350], "cruise_fractions": [0.6, 0.6],
                                          "step_climb_fpm": 1000, "climb_min": 20, "descent_min": 20})  # fmt: skip


def test_synthetic_trajectory_time_order_duration_and_label():
    tr = synthesize_geodesic(SCL, MEL, constant(), 780, DEP, 5)
    p = tr.points
    assert tr.synthetic and tr.label == SYNTHETIC_LABEL
    assert p["t_min"].iloc[0] == 0 and p["t_min"].iloc[-1] == 780
    assert p["t_min"].is_monotonic_increasing and p["t_min"].is_unique
    assert tr.has_integer_minutes
    assert p["timestamp_utc"].iloc[-1] - p["timestamp_utc"].iloc[0] == pd.Timedelta(minutes=780)
    assert str(p["timestamp_utc"].dt.tz) == "UTC"
    assert (p["lat"].iloc[-1], p["lon"].iloc[-1]) == pytest.approx((MEL.lat, MEL.lon))
    assert tr.total_distance_km == pytest.approx(tr.meta["geodesic_distance_km"], rel=1e-9)
    assert tr.southernmost()["lat"] < -66.0
    assert np.all(np.abs(np.diff(p["lon_unwrapped"])) < 5)  # no ±360° jump
    assert set(p["phase"]) == {"ascenso", "crucero", "descenso"}


def test_sampling_includes_profile_breakpoints():
    tr = synthesize_geodesic(SCL, MEL, step(), 780, DEP, 5)
    knots = tr.meta["profile_knots_min"]
    assert set(knots) <= set(tr.points["t_min"])


def test_sampling_requires_timezone():
    with pytest.raises(ValueError):
        synthesize_geodesic(SCL, MEL, constant(), 780, pd.Timestamp("2020-02-15T03:00"), 5)


def test_csv_import_requires_explicit_altitude_metadata():
    with pytest.raises(ValueError):
        import_csv(FIX / "synthetic_track.csv", altitude_unit=None, altitude_reference="pressure_altitude")
    with pytest.raises(ValueError):
        import_csv(FIX / "synthetic_track.csv", altitude_unit="m", altitude_reference=None)


def test_csv_import_and_resample_across_antimeridian():
    tr = import_csv(FIX / "synthetic_track.csv", "m", "pressure_altitude", synthetic=True)
    assert tr.duration_min == pytest.approx(40.25)
    assert not tr.has_integer_minutes
    r = tr.resample_minutes(1)
    t = r.points["t_min"].to_numpy()
    assert t[0] == 0 and t[-1] == 40 and np.all(np.diff(t) == 1)
    assert any("descartan" in w for w in r.warnings)
    assert np.all(np.abs(np.diff(r.points["lon_unwrapped"])) < 1)
    ft, _ = r.cari_altitude_ft()
    assert ft[21] == pytest.approx(37000.0)  # 11277.6 m pressure altitude = FL370


def test_csv_import_rejects_unordered_time(tmp_path):
    df = pd.read_csv(FIX / "synthetic_track.csv")
    df.iloc[[1, 2]] = df.iloc[[2, 1]].to_numpy()
    f = tmp_path / "bad.csv"
    df.to_csv(f, index=False)
    with pytest.raises(ValueError):
        import_csv(f, "m", "pressure_altitude")


def test_via_waypoints_follow_polyline_and_keep_constant_speed():
    via = [(-55.0, 170.0), (-70.0, -160.0), (-60.0, -100.0)]  # crosses the antimeridian
    tr = synthesize_geodesic(SCL, MEL, constant(), 900, DEP, 1, via=via[::-1])
    p = tr.points
    assert tr.label == VIA_LABEL and tr.meta["n_via_waypoints"] == 3
    assert tr.meta["path_distance_km"] > tr.meta["geodesic_distance_km"]
    for la, lo in via:  # the track passes through every waypoint (within one 1-min sampling step)
        _, _, d = WGS84.inv(np.full(len(p), lo), np.full(len(p), la), p["lon"], p["lat"])
        assert d.min() < 15e3
    assert (p["lat"].iloc[0], p["lat"].iloc[-1]) == pytest.approx((SCL.lat, MEL.lat))
    step_km = np.diff(p["cum_dist_km"].to_numpy())
    assert step_km.max() / step_km.min() < 1.01  # constant ground speed along the polyline
    assert p["cum_dist_km"].iloc[-1] == pytest.approx(tr.meta["path_distance_km"], rel=1e-3)
