# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Reproducible scenario study of galactic cosmic radiation (GCR) dose for aircrew on southern routes
from Santiago (SCL–MEL/SYD/AKL/PUQ), using the FAA's **CARI-7** as the only dose engine. Docs, configs,
figures and commit messages are in Spanish; code identifiers and code comments are in English.
`HANDOFF.md` holds the current state, the included runs and the pending work. Read it first.

## Commands

```bash
uv sync                                                  # deps (Python 3.13, uv)
uv run python scripts/install_cari7.py                   # downloads CARI-7 from the FAA into third_party/cari7/ (hash-verified)
uv run airrad check                                      # runs the official EXAMPLE.DEG, must report "identical": true
uv run pytest -q -m "not cari"                           # fast tests (synthetic fixtures, no CARI)
uv run pytest -q                                         # + the "cari" test (needs CARI installed and Docker)
uv run pytest tests/test_dosimetry_annual.py::test_mixed_calendar_with_explicit_directions   # single test
uv run airrad scenarios --config config/scl_puq.yaml     # list the scenario matrix
uv run airrad run --config config/<x>.yaml --run-id <id> [--block B] [--contains S] [--dry-run]
uv run airrad report runs/<id> [--no-figures]            # rebuild report/ (CSV + figures) without calling CARI
uv run python scripts/build_notebook.py runs/<id>        # regenerate and execute notebooks/analisis_inicial.ipynb
```

There is no linter config. The code uses long lines and `# fmt: skip` on hand-aligned statements, so
match that style.

**Running CARI.** CARI-7 is a Linux x86-64 binary, run in Docker with `--platform linux/amd64`. On
this Mac that means Colima with Rosetta (`colima start --vz-rosetta --cpu 10`). Colima only mounts
`$HOME`. `engine.max_parallel` in each config is the number of concurrent containers; keep it at
roughly the VM's vCPU count.

## Architecture

The pipeline is **config YAML → scenarios → trajectories → CARI batches → parsed results → run
directory → report**.

- **`config/*.yaml`** define routes, `via` waypoints, altitude profiles, durations (ground speed or
  fixed minutes per route and direction), dates, a `matrix` of named blocks, `report` options and
  `annual` calendars. `scenarios.py` expands the blocks into `Scenario`s. Each block lists its own
  directions; the top-level `directions` key is not used by the matrix.
- **`trajectory.py`** builds the flight path in one of three ways:
  - a synthetic WGS84 geodesic;
  - geodesics through approximate waypoints (`via`, e.g. `data/tracks/*digitized.csv`);
  - an imported CSV track with explicit pressure-altitude metadata.

  It samples at integer minutes, which CARI needs, and puts the profile breakpoints into the sampling.
  Synthetic tracks carry `SYNTHETIC_LABEL` / `VIA_LABEL`, which must be shown wherever the track is
  shown.
- **`engines/cari7.py`** implements the `DoseEngine` protocol from `engines/base.py`:
  - It groups requests by (quantity, year, month), because one batch shares `DEFAULT.INP` (the tally)
    and the GCR spectrum file (the date).
  - It splits each group over `max_parallel` work dirs, `runs/<id>/cari_work/Bnn_<qty>_<yyyymm>/`.
  - It writes the `.DEG` inputs and runs each batch in its own container.
  - It parses the `.SUM` totals and the per-minute `.DAT` rates.
  - With `docker_local_copy: true` (the default), each container copies the CARI data dirs plus the
    batch inputs to its own disk, which is about 10× faster than virtiofs.
  - **Never copy the CARI install root into a work dir.** A stray `.DEG` such as `EXAMPLE.DEG` makes
    CARI carry its date into the next flight (`docs/cari7_verificacion.md` §2).
- **`pipeline.py`** writes an immutable run directory: `run_study` fails if it exists, so new
  matrices need a new `--run-id`. The directory holds `config.yaml`, `manifest.json` (hashes of the
  binary, data files and config, plus git state), `scenarios.csv`, `trajectories.csv`,
  `flights_raw.csv` and `steps.csv`. Committed runs are the study's evidence; don't rewrite them.
  Regenerating `report/` is fine.
- **`report.py`** rebuilds everything under `report/` from those files:
  - It calls `dosimetry.py` for the per-flight summaries and the comparisons against
    `report.reference_route`.
  - It calls `annual.py` for the calendars. A mixed-calendar key `"ROUTE"` means the mean of both
    directions; `"ROUTE direction"` means that direction only.
  - It calls `validation.py`, which checks per flight that Σ rate·Δt matches CARI's total
    (|Δ| < 1e-3), that CARI's evaluated positions match the trajectory, and the atmospheric depth.
  - It calls `plotting.py` for the figures. `plotting.route_direction` picks the direction shown per
    route: the one with the most scenarios, ties going to outbound.
- **`quantities.py` / `units.py`** keep effective dose (ICRP 103), H*(10) and absorbed dose as
  distinct quantities. `require_single_quantity` guards against mixing them.

## Scientific rules (from the original brief — enforce them in code and text)

- **Doses come only from CARI-7.** Don't add empirical dose formulas, and no multipliers for the
  South Atlantic Anomaly, "polar routes" or latitude. Don't treat magnetic-field strength as cutoff
  rigidity.
- **No assumed physics.** Don't presume that more solar activity means more GCR, and don't invent
  physical differences between directions.
- **Quantities stay separate.** Never interchange effective dose, H*(10) and absorbed dose, and
  never integrate values that are already doses a second time.
- **No invented uncertainty or risk.** No made-up confidence intervals, no conversion to cancer
  risk and no clinical conclusions.
- **Annual figures are approximations.** Label them as such, and never claim that a calendar
  complies with labour or duty limits.
- **Keep data honest.** Synthetic or test data stays separate and labelled (`tests/fixtures/`), and
  is never used for conclusions. Commercial schedules are not airborne times. Compare with the
  literature only under comparable conditions, without tuning factors.
- **Scope.** GCR only: SPE/GLE are out of scope. No web platform, database or cloud infrastructure.
- **Don't redistribute CARI-7 binaries or data.** `third_party/cari7/*` and
  `validation/official_example/*/EXAMPLE.DEG` are git-ignored.
- **Don't commit unless the user asks.**
