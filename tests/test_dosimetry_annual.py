"""Integration, aggregation and calendars on SYNTHETIC numbers (not physical results)."""

import numpy as np
import pandas as pd
import pytest

from airrad.annual import annual_table
from airrad.dosimetry import comparisons, rate_integral, time_weighted_mean_rate
from airrad.quantities import Quantity, require_single_quantity


def steps(rates):
    n = len(rates)
    return pd.DataFrame({"t_start_min": np.arange(n, dtype=float), "t_end_min": np.arange(1, n + 1, dtype=float),
                         "rate": rates})  # fmt: skip


def test_rate_integral_midpoint_rule_units():
    st = steps([6.0] * 120)  # 6 µSv/h for 2 h
    assert rate_integral(st) == pytest.approx(12.0)
    assert time_weighted_mean_rate(st) == pytest.approx(6.0)


def test_time_weighted_mean_times_duration_equals_integral():
    rng = np.random.default_rng(1)
    st = steps(rng.uniform(0.0, 8.0, 777))
    T_h = 777 / 60
    assert time_weighted_mean_rate(st) * T_h == pytest.approx(rate_integral(st))


def test_quantities_are_not_mixed():
    with pytest.raises(ValueError):
        require_single_quantity(["E_ICRP103", "H10"])
    assert Quantity.from_key("H10").info.cari_tally == 4
    assert Quantity.from_key("D_WB").info.dose_unit == "µGy"


def summary_rows():
    rows = []
    for route, dose in (("SCL-MEL", 70.0), ("SCL-AKL", 50.0)):
        for direction, d in (("outbound", dose), ("inbound", dose + 2.0)):
            for date, f in (("2020-02", 1.0), ("2024-10", 0.8)):
                rows.append({"scenario_id": f"{route}_{direction}_{date}", "route": route, "direction": direction,
                             "profile": "FL370", "duration": "gs470", "date": date, "quantity": "E_ICRP103",
                             "sampling_min": 5.0, "total_dose": d * f, "airborne_h": 12.0, "airborne_min": 720,
                             "dose_per_flight_hour": d * f / 12.0, "dose_unit": "µSv"})  # fmt: skip
    return pd.DataFrame(rows)


def test_annual_leg_is_one_way_and_rotation_is_two_legs():
    cfg = {"months": 12, "legs_per_month": [2, 8], "representative": {"profile": "FL370", "duration": "gs470"},
           "mixed_calendars": [{"name": "mix", "legs_per_month": {"SCL-MEL": 2, "SCL-AKL": 4}}]}  # fmt: skip
    a = annual_table(summary_rows(), cfg)
    r = a[(a.routes == "SCL-MEL") & (a.date == "2020-02") & (a.legs_per_month == 2)].iloc[0]
    assert r.legs_total == 24 and r.rotations_equivalent == 12
    assert r.annual_dose_uSv == pytest.approx(24 * 71.0)  # mean of both directions per leg
    assert r.annual_dose_mSv == pytest.approx(24 * 71.0 / 1000)
    assert r.annual_hours == pytest.approx(24 * 12.0)
    m = a[(a.kind == "mixto") & (a.date == "2020-02")].iloc[0]
    assert m.legs_total == 72
    assert m.annual_dose_uSv == pytest.approx(24 * 71.0 + 48 * 51.0)
    assert "aproximación" in m.method


def test_mixed_calendar_with_explicit_directions():
    cfg = {"months": 12, "legs_per_month": [], "representative": {"profile": "FL370", "duration": "gs470"},
           "mixed_calendars": [{"name": "rot", "kind": "rotación",
                                "legs_per_month": {"SCL-MEL outbound": 2, "SCL-AKL inbound": 2}}]}  # fmt: skip
    m = annual_table(summary_rows(), cfg)
    r = m[m.date == "2020-02"].iloc[0]
    assert r.kind == "rotación" and r.legs_total == 48
    assert r.annual_dose_uSv == pytest.approx(24 * 70.0 + 24 * 52.0)  # outbound 70, inbound 50 + 2


def test_comparisons_absolute_and_percent():
    c = comparisons(summary_rows())
    d = c[(c.varied == "date") & (c.route == "SCL-MEL") & (c.direction == "outbound")].iloc[0]
    assert d.diff_abs == pytest.approx(70.0 * 0.8 - 70.0)
    assert d.diff_pct == pytest.approx(-20.0)
    r = c[(c.varied == "route") & (c.direction == "outbound") & (c.date == "2020-02")].iloc[0]
    assert r.value == "SCL-AKL" and r.diff_pct == pytest.approx((50 / 70 - 1) * 100)
