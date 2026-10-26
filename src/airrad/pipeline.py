"""Batch execution of a study: trajectories -> engine -> raw tables + manifest."""

from __future__ import annotations

import json
import shutil
import traceback
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .engines.base import FlightRequest
from .engines.cari7 import Cari7Config, Cari7Engine
from .provenance import SOURCES, environment, git_state, sha256_file, write_manifest
from .scenarios import Scenario, Study

GLOBAL_ASSUMPTIONS = [
    "Sólo radiación cósmica galáctica (GCR). Eventos de partículas solares (SPE/GLE) fuera del alcance.",
    "Condiciones promedio mensuales de CARI-7 (día=00): sin ajustes horarios por decrecimientos Forbush ni Kp.",
    "Trayectorias geodésicas sintéticas WGS84; no representan rutas operacionales (vientos, ETOPS, ATC).",
    "Perfiles verticales, duraciones y velocidades son supuestos configurables, no datos de vuelos reales.",
    "Altitudes de perfil = altitud de presión ISA (FL x 100 ft), que CARI interpreta como altitud "
    "geopotencial de la Atmósfera Estándar EE.UU. 1976.",
    "Sin blindaje del fuselaje (práctica habitual; CARI-7 no lo modela).",
    "Sin multiplicadores ad hoc (Anomalía del Atlántico Sur, polo, 'ruta polar'): el blindaje geomagnético "
    "lo representa CARI mediante rigideces de corte.",
    "CARI-7 usa la rejilla de rigidez de corte IGRF2010 para fechas >= 2010 (sin variación secular posterior).",
]


def make_engine(study: Study) -> Cari7Engine:
    cfg = study.raw["engine"]
    if cfg["name"] != "cari7":
        raise ValueError(f"Motor no soportado: {cfg['name']}")
    return Cari7Engine(Cari7Config.from_dict(cfg, study.root))


def select(scenarios: list[Scenario], blocks=None, contains=None) -> list[Scenario]:
    out = scenarios
    if blocks:
        out = [s for s in out if set(s.blocks) & set(blocks)]
    if contains:
        out = [s for s in out if all(c in s.scenario_id for c in contains)]
    return out


def run_study(config_path, run_id: str | None = None, blocks=None, contains=None, dry_run: bool = False) -> Path:
    study = Study.load(config_path)
    scenarios = select(study.scenarios(), blocks, contains)
    if not scenarios:
        raise ValueError("La selección no contiene escenarios")
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = study.root / study.raw["study"].get("runs_dir", "runs") / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    shutil.copy2(study.path, run_dir / "config.yaml")
    started = datetime.now(timezone.utc)

    trajs, traj_rows, traj_meta = {}, [], {}
    for sc in scenarios:
        tr = study.trajectory(sc)
        trajs[sc.scenario_id] = tr
        df = tr.points.copy()
        df.insert(0, "scenario_id", sc.scenario_id)
        df["altitude_reference"] = tr.altitude_reference
        df["synthetic"] = tr.synthetic
        traj_rows.append(df)
        traj_meta[sc.scenario_id] = {
            "label": tr.label, "synthetic": tr.synthetic, "meta": tr.meta,
            "southernmost": tr.southernmost(), "distance_km": tr.total_distance_km, "warnings": tr.warnings,
        }  # fmt: skip
    pd.DataFrame([s.row() for s in scenarios]).to_csv(run_dir / "scenarios.csv", index=False)
    pd.concat(traj_rows).to_csv(run_dir / "trajectories.csv", index=False)
    (run_dir / "trajectories_meta.json").write_text(json.dumps(traj_meta, indent=2, ensure_ascii=False, default=str))

    engine = make_engine(study)
    install_prov = study.root / "third_party" / "cari7" / "INSTALL_PROVENANCE.json"
    manifest = dict(
        run_id=run_id,
        purpose=study.raw["study"]["description"],
        config_file=str(study.path.relative_to(study.root)),
        config_sha256=sha256_file(study.path),
        config=study.raw,
        n_scenarios=len(scenarios),
        selection={"blocks": blocks, "contains": contains},
        airports_provenance=study.airports_provenance,
        cari_install_provenance=json.loads(install_prov.read_text()) if install_prov.exists() else None,
        git=git_state(study.root),
        environment=environment(study.root),
        sources=SOURCES,
        assumptions=GLOBAL_ASSUMPTIONS,
        started_utc=started.isoformat(timespec="seconds"),
    )
    problems = engine.check_installation()
    if problems or dry_run:
        manifest.update(status="dry-run" if dry_run else "engine-unavailable", engine_problems=problems)
        write_manifest(run_dir / "manifest.json", **manifest)
        if problems and not dry_run:
            raise RuntimeError("CARI-7 no disponible; trayectorias escritas en " + str(run_dir) + "\n" + "\n".join(problems))
        return run_dir
    manifest["engine"] = engine.describe()
    requests = [FlightRequest(s.scenario_id, trajs[s.scenario_id], s.year, s.month, s.quantity) for s in scenarios]
    try:
        results = engine.run(requests, run_dir)
    except Exception as exc:
        manifest.update(status="failed", error=repr(exc), traceback=traceback.format_exc())
        write_manifest(run_dir / "manifest.json", **manifest)
        raise

    by_id = {s.scenario_id: s for s in scenarios}
    flights, steps, per_warn, batches = [], [], {}, {}
    for r in results:
        sc = by_id[r.scenario_id]
        flights.append(
            {
                **sc.row(),
                "engine": r.engine,
                "total_dose_engine": r.total_dose,
                "dose_unit": r.quantity.info.dose_unit,
                "quantity_label": r.quantity.info.label_es,
                "heliocentric_potential_MV": r.conditions.get("heliocentric_potential_MV"),
                "cari_date": r.conditions.get("date"),
                "synthetic_trajectory": trajs[r.scenario_id].synthetic,
                "raw_sum": str(r.raw_files["sum"].relative_to(run_dir)),
                "raw_dat": str(r.raw_files["dat"].relative_to(run_dir)),
                "raw_deg": str(r.raw_files["deg"].relative_to(run_dir)),
            }
        )
        st = r.steps.copy()
        st.insert(0, "scenario_id", r.scenario_id)
        steps.append(st)
        per_warn[r.scenario_id] = r.warnings
        b = r.conditions["batch"]
        batches[json.dumps(b["command"])] = b  # one entry per engine invocation
    pd.DataFrame(flights).to_csv(run_dir / "flights_raw.csv", index=False)
    pd.concat(steps).to_csv(run_dir / "steps.csv", index=False)
    manifest.update(
        status="ok",
        finished_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        scenario_warnings=per_warn,
        batches=list(batches.values()),
    )
    write_manifest(run_dir / "manifest.json", **manifest)
    return run_dir
