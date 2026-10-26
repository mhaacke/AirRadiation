"""Consistency checks between the trajectories sent and what the engine evaluated."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import geodesy
from .engines.cari7 import load_ft_gm_table


def check_flight(st: pd.DataFrame, tr: pd.DataFrame, total_engine: float, ft_gm: pd.DataFrame | None) -> dict:
    st = st.sort_values("step")
    tr = tr.sort_values("t_min")
    t_mid = st["t_mid_min"].to_numpy()
    out = {
        "n_steps": len(st),
        "expected_steps": int(round(tr["t_min"].iloc[-1])),
        "time_strictly_increasing": bool(np.all(np.diff(st["t_mid_min"]) > 0) and np.all(np.diff(tr["t_min"]) > 0)),
        "unit_steps_1min": bool(np.allclose(st["t_end_min"] - st["t_start_min"], 1.0)),
        "cum_dose_monotonic": bool(np.all(np.diff(st["cum_dose"]) >= -1e-9)),
        "rates_non_negative": bool((st["rate"] >= 0).all()),
    }
    integral = float((st["rate"] / 60.0).sum())
    out["integral_rel_diff"] = integral / total_engine - 1.0
    mean = float(st["rate"].mean())  # unit steps -> time-weighted mean
    out["mean_rate_x_hours_rel_diff"] = mean * len(st) / 60.0 / total_engine - 1.0
    # Position actually evaluated by CARI vs. our geodesic at the same time.
    lat_i, lon_i = [], []
    t_tr = tr["t_min"].to_numpy()
    for t in t_mid:
        j = int(np.clip(np.searchsorted(t_tr, t, side="right") - 1, 0, len(t_tr) - 2))
        frac = (t - t_tr[j]) / (t_tr[j + 1] - t_tr[j])
        a, b = tr.iloc[j], tr.iloc[j + 1]
        la, lo = geodesy.interpolate_on_segment(a.lat, a.lon, b.lat, b.lon, frac)
        lat_i.append(la)
        lon_i.append(lo)
    _, _, dist = geodesy.WGS84.inv(np.array(lon_i), np.array(lat_i), st["lon"].to_numpy(), st["lat"].to_numpy())
    out["max_position_offset_km"] = float(np.max(dist) / 1000.0)
    # Altitude convention: depth CARI used vs. depth of our pressure altitude in CARI's own table.
    if ft_gm is not None and (tr["altitude_reference"] == "pressure_altitude").all():
        alt_mid = np.interp(t_mid, t_tr, tr["alt_ft"].to_numpy())
        logd = np.interp(alt_mid, ft_gm["alt_ft"], np.log(ft_gm["depth_g_cm2"]))
        rel = st["depth_g_cm2"].to_numpy() / np.exp(logd) - 1.0
        out["max_depth_rel_diff"] = float(np.max(np.abs(rel)))
        on_table = np.isin(np.round(alt_mid, 6), ft_gm["alt_ft"].to_numpy())
        out["max_depth_rel_diff_on_table_nodes"] = float(np.max(np.abs(rel[on_table]))) if on_table.any() else None
    out["antimeridian_crossed"] = geodesy.crosses_antimeridian(tr["lon"].to_numpy())
    depth_nodes = out.get("max_depth_rel_diff_on_table_nodes")
    out["ok"] = bool(
        out["n_steps"] == out["expected_steps"]
        and out["time_strictly_increasing"]
        and out["unit_steps_1min"]
        and out["cum_dose_monotonic"]
        and abs(out["integral_rel_diff"]) < 1e-3  # .DAT rates are printed with 5 significant digits
        and out["max_position_offset_km"] < 1.0
        and (depth_nodes is None or depth_nodes < 1e-4)
    )
    return out


def check_run(flights: pd.DataFrame, steps: pd.DataFrame, traj: pd.DataFrame, install_dir: Path | None) -> pd.DataFrame:
    ft_gm = load_ft_gm_table(install_dir) if install_dir and (install_dir / "ATMOSPHERE").exists() else None
    rows = []
    for f in flights.itertuples(index=False):
        r = check_flight(
            steps[steps["scenario_id"] == f.scenario_id],
            traj[traj["scenario_id"] == f.scenario_id],
            float(f.total_dose_engine),
            ft_gm,
        )
        rows.append({"scenario_id": f.scenario_id, **r})
    return pd.DataFrame(rows)
