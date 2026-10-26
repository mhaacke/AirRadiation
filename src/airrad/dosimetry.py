"""Integration, aggregation and comparison of engine results.

The engine-reported flight dose (CARI .SUM) is the reference value. The
integral of the local rates is recomputed only as a consistency check, with
the same rule CARI uses (one-minute steps, rate at the step midpoint):
dose = sum(rate_i * dt_i), dt in hours. The cumulative column of the .DAT is
already a dose and is never integrated again.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .quantities import Quantity, require_single_quantity
from .units import usv_to_msv

KEY_COLS = ["route", "direction", "profile", "duration", "date", "quantity", "sampling_min"]


def rate_integral(steps: pd.DataFrame) -> float:
    dt_h = (steps["t_end_min"] - steps["t_start_min"]) / 60.0
    return float((steps["rate"] * dt_h).sum())


def time_weighted_mean_rate(steps: pd.DataFrame) -> float:
    dt = steps["t_end_min"] - steps["t_start_min"]
    return float((steps["rate"] * dt).sum() / dt.sum())


def flight_summary(flights_raw: pd.DataFrame, steps: pd.DataFrame, traj: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for f in flights_raw.itertuples(index=False):
        st = steps[steps["scenario_id"] == f.scenario_id].sort_values("step")
        tr = traj[traj["scenario_id"] == f.scenario_id].sort_values("t_min")
        q = Quantity.from_key(f.quantity)
        T_h = (st["t_end_min"].iloc[-1] - st["t_start_min"].iloc[0]) / 60.0
        integral = rate_integral(st)
        mean_rate = time_weighted_mean_rate(st)
        imax = st["rate"].idxmax()
        if "phase" in tr and tr["phase"].notna().any():
            cr = tr[tr["phase"] == "crucero"]["t_min"]
            in_cruise = (st["t_mid_min"] >= cr.min()) & (st["t_mid_min"] <= cr.max())
            cruise_mean = time_weighted_mean_rate(st[in_cruise]) if in_cruise.any() else np.nan
        else:
            cruise_mean = np.nan
        rows.append(
            {
                **{c: getattr(f, c) for c in ["scenario_id", *KEY_COLS, "origin", "destination", "blocks"]},
                "engine": f.engine,
                "quantity_label": q.info.label_es,
                "dose_unit": q.info.dose_unit,
                "rate_unit": q.info.rate_unit,
                "airborne_min": int(f.airborne_min),
                "airborne_h": T_h,
                "distance_km": float(tr["cum_dist_km"].iloc[-1]),
                "southernmost_lat": float(tr["lat"].min()),
                "heliocentric_potential_MV": f.heliocentric_potential_MV,
                "total_dose": float(f.total_dose_engine),
                "total_dose_milli": float(usv_to_msv(f.total_dose_engine)),
                "dose_unit_milli": q.info.dose_unit.replace("µ", "m"),
                "integral_from_rates": integral,
                "integral_rel_diff": integral / float(f.total_dose_engine) - 1.0,
                "mean_rate": mean_rate,
                "dose_per_flight_hour": float(f.total_dose_engine) / T_h,
                "cruise_mean_rate": cruise_mean,
                "max_rate": float(st.loc[imax, "rate"]),
                "max_rate_t_min": float(st.loc[imax, "t_mid_min"]),
                "max_rate_lat": float(st.loc[imax, "lat"]),
                "max_rate_lon": float(st.loc[imax, "lon"]),
                "synthetic_trajectory": bool(f.synthetic_trajectory),
            }
        )
    return pd.DataFrame(rows)


def _pairs(summary, vary: str, ref_value, label: str) -> list[dict]:
    """Compare every scenario with the one differing only in `vary` = ref_value."""
    keys = [c for c in KEY_COLS if c != vary]
    out = []
    for _, grp in summary.groupby(keys, dropna=False):
        require_single_quantity(grp["quantity"])
        ref = grp[grp[vary] == ref_value]
        if ref.empty:
            continue
        r = ref.iloc[0]
        for _, s in grp[grp[vary] != ref_value].iterrows():
            out.append(
                {
                    "comparison": label,
                    "varied": vary,
                    "reference": ref_value,
                    "value": s[vary],
                    **{k: s[k] for k in keys},
                    "scenario_ref": r["scenario_id"],
                    "scenario": s["scenario_id"],
                    "dose_ref": r["total_dose"],
                    "dose": s["total_dose"],
                    "dose_unit": s["dose_unit"],
                    "diff_abs": s["total_dose"] - r["total_dose"],
                    "diff_pct": 100.0 * (s["total_dose"] / r["total_dose"] - 1.0),
                    "airborne_min_ref": r["airborne_min"],
                    "airborne_min": s["airborne_min"],
                    "dose_per_h_ref": r["dose_per_flight_hour"],
                    "dose_per_h": s["dose_per_flight_hour"],
                    "dose_per_h_diff_pct": 100.0 * (s["dose_per_flight_hour"] / r["dose_per_flight_hour"] - 1.0),
                }
            )
    return out


def comparisons(summary: pd.DataFrame, reference_route: str = "SCL-MEL") -> pd.DataFrame:
    """Absolute and percentage differences between scenarios (same quantity only)."""
    s = summary[summary["route"].str.startswith("SCL-")]
    rows = []
    rows += _pairs(s, "date", "2020-02", "fecha (modulación solar)")
    rows += _pairs(s, "profile", "FL370", "perfil de altura")
    rows += _pairs(s, "route", reference_route, "ruta")
    rows += _pairs(s, "direction", "outbound", "sentido")
    rows += _pairs(s, "duration", "gs470", "duración")
    rows += _pairs(s, "sampling_min", 5.0, "convergencia (paso de muestreo)")
    return pd.DataFrame(rows)


def quantity_table(summary: pd.DataFrame) -> pd.DataFrame:
    """Side-by-side quantities for the same flight. Not differences: they are distinct quantities."""
    s = summary[summary["blocks"].str.contains("magnitudes")]
    keys = ["route", "direction", "profile", "duration", "date", "sampling_min"]
    wide = s.pivot_table(index=keys, columns="quantity", values="total_dose").reset_index()
    if {"H10", "E_ICRP103"} <= set(wide.columns):
        wide["ratio_H10_over_E"] = wide["H10"] / wide["E_ICRP103"]
    return wide


def cumulative_series(steps: pd.DataFrame, scenario_id: str) -> pd.DataFrame:
    st = steps[steps["scenario_id"] == scenario_id].sort_values("step")
    first = pd.DataFrame({"t_min": [st["t_start_min"].iloc[0]], "cum_dose": [0.0]})
    return pd.concat([first, pd.DataFrame({"t_min": st["t_end_min"], "cum_dose": st["cum_dose"]})], ignore_index=True)
