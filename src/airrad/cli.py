"""Command line interface.

  airrad check     [--config config/study.yaml]   instalación + ejemplo oficial de CARI-7
  airrad scenarios [--config ...]                 lista la matriz de escenarios
  airrad run       [--config ...] [--block B] [--contains TEXT] [--run-id ID] [--dry-run]
  airrad report    RUN_DIR                        tablas, validaciones y figuras
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

DEFAULT_CONFIG = "config/study.yaml"


def cmd_check(args) -> int:
    from .pipeline import make_engine
    from .scenarios import Study

    study = Study.load(args.config)
    engine = make_engine(study)
    problems = engine.check_installation()
    if problems:
        print("CARI-7 no utilizable:\n- " + "\n- ".join(problems))
        print("Instalación: uv run python scripts/install_cari7.py")
        return 2
    desc = engine.describe()
    out_dir = study.root / "validation" / "official_example"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    res = engine.run_official_example(out_dir / stamp)
    report = {"checked_utc": stamp, "engine": desc, "official_example": res}
    (out_dir / stamp / "check.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    print(json.dumps({k: res[k] for k in res if k != "run"}, indent=2, ensure_ascii=False))
    print(f"Binario {desc['executable']} sha256={desc['executable_sha256']} banner={desc['embedded_banner']!r}")
    return 0 if res["identical"] else 1


def cmd_scenarios(args) -> int:
    from .scenarios import Study

    sc = Study.load(args.config).scenarios()
    df = pd.DataFrame([s.row() for s in sc])
    with pd.option_context("display.max_rows", None, "display.width", 200):
        print(df[["scenario_id", "airborne_min", "blocks"]].to_string(index=False))
    print(f"{len(df)} escenarios")
    return 0


def cmd_run(args) -> int:
    from .pipeline import run_study

    run_dir = run_study(args.config, args.run_id, args.block, args.contains, args.dry_run)
    print(f"Resultados en {run_dir}")
    return 0


def cmd_report(args) -> int:
    from .report import build_report

    out = build_report(Path(args.run_dir), figures=not args.no_figures)
    print(f"Informe en {out}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="airrad", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("check", cmd_check), ("scenarios", cmd_scenarios), ("run", cmd_run)):
        p = sub.add_parser(name)
        p.add_argument("--config", default=DEFAULT_CONFIG)
        p.set_defaults(fn=fn)
        if name == "run":
            p.add_argument("--block", action="append", help="limitar a uno o más bloques de la matriz")
            p.add_argument("--contains", action="append", help="limitar a ids que contengan el texto")
            p.add_argument("--run-id")
            p.add_argument("--dry-run", action="store_true", help="sólo trayectorias y manifiesto")
    p = sub.add_parser("report")
    p.add_argument("run_dir")
    p.add_argument("--no-figures", action="store_true")
    p.set_defaults(fn=cmd_report)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
