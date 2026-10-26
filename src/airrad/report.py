"""Build tables, validation results and figures for a finished run."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml

from . import plotting
from .annual import annual_table
from .dosimetry import comparisons, flight_summary, quantity_table
from .validation import check_run


def load_run(run_dir: Path) -> dict:
    run_dir = Path(run_dir)
    return {
        "config": yaml.safe_load((run_dir / "config.yaml").read_text()),
        "manifest": json.loads((run_dir / "manifest.json").read_text()),
        "flights": pd.read_csv(run_dir / "flights_raw.csv"),
        "steps": pd.read_csv(run_dir / "steps.csv"),
        "traj": pd.read_csv(run_dir / "trajectories.csv"),
    }


def build_report(run_dir: Path, figures: bool = True) -> Path:
    run_dir = Path(run_dir)
    d = load_run(run_dir)
    out = run_dir / "report"
    (out / "figures").mkdir(parents=True, exist_ok=True)
    summary = flight_summary(d["flights"], d["steps"], d["traj"])
    summary.to_csv(out / "flights_summary.csv", index=False)
    rep_cfg = d["config"].get("report", {})
    comp = comparisons(summary, rep_cfg.get("reference_route", "SCL-MEL"))
    comp.to_csv(out / "comparisons.csv", index=False)
    quantity_table(summary).to_csv(out / "quantities_same_flight.csv", index=False)
    annual = annual_table(summary, d["config"]["annual"])
    annual.to_csv(out / "annual_calendars.csv", index=False)

    root = run_dir.parents[1]
    install = root / d["config"]["engine"]["install_dir"]
    checks = check_run(d["flights"], d["steps"], d["traj"], install)
    checks.to_csv(out / "validation_checks.csv", index=False)
    conv = comp[comp["varied"] == "sampling_min"] if not comp.empty else pd.DataFrame(
        columns=["scenario_ref", "scenario", "dose_ref", "dose", "diff_pct"]
    )
    validation = {
        "all_flight_checks_ok": bool(checks["ok"].all()),
        "n_flights": len(checks),
        "max_abs_integral_rel_diff": float(checks["integral_rel_diff"].abs().max()),
        "max_position_offset_km": float(checks["max_position_offset_km"].max()),
        "max_depth_rel_diff_on_table_nodes": float(checks["max_depth_rel_diff_on_table_nodes"].max()),
        "max_depth_rel_diff_any": float(checks["max_depth_rel_diff"].max()),
        "convergence": conv[["scenario_ref", "scenario", "dose_ref", "dose", "diff_pct"]].to_dict("records"),
    }
    (out / "validation_summary.json").write_text(json.dumps(validation, indent=2, ensure_ascii=False))

    if figures:
        plotting.DATA_NOTES[:] = [
            f"Ruta {k}: {plotting.VIA_LABEL}." for k, v in d["config"]["routes"].items() if v.get("via")
        ]
        fig = out / "figures"
        plotting.map_routes(d["traj"], summary, fig / "mapa_rutas.png")
        for date in sorted(summary.date.unique()):
            plotting.map_dose_rate(d["traj"], d["steps"], summary, fig / f"mapa_tasa_{date}.png", date)
        profiles = rep_cfg.get("rate_altitude_profiles", ["FL370", "STEP330-390"])
        for route in plotting.ROUTE_ORDER:
            if route in set(summary.route):
                direction = plotting.route_direction(summary, route)
                short = {"outbound": "out", "inbound": "in"}[direction]
                plotting.rate_and_altitude(d["traj"], d["steps"], summary, fig / f"tasa_altitud_{route}_{short}.png", route,
                                           direction=direction, profiles=profiles)  # fmt: skip
        plotting.cumulative_dose(d["steps"], summary, fig / "dosis_acumulada.png")
        plotting.total_dose_bars(summary, fig / "dosis_total_rutas_perfiles.png")
        rep = d["config"]["annual"]["representative"]
        if not annual.empty:
            plotting.annual_exposure(annual, fig / "exposicion_anual.png", f"{rep['profile']}, {rep['duration']}")
            plotting.annual_cumulative(annual, fig / "acumulacion_anual.png", f"{rep['profile']}, {rep['duration']}")
    return out
