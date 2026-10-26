"""Engine-independent interface between trajectories and dose models.

An engine receives flight requests and returns, per flight, the total dose as
reported by the engine plus (if available) the local dose-rate profile. The
analysis layer only depends on these structures, so CARI-7A or another model
can be added as a new engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import pandas as pd

from ..quantities import Quantity
from ..trajectory import Trajectory


@dataclass(frozen=True)
class FlightRequest:
    scenario_id: str
    trajectory: Trajectory
    year: int
    month: int  # monthly-average conditions (galactic cosmic radiation only)
    quantity: Quantity = Quantity.EFFECTIVE_DOSE_ICRP103


@dataclass
class FlightResult:
    scenario_id: str
    quantity: Quantity
    engine: str
    total_dose: float  # engine-reported integral, in quantity.info.dose_unit
    steps: pd.DataFrame | None  # t_start_min, t_mid_min, t_end_min, lat, lon, depth_g_cm2, rate, cum_dose
    raw_files: dict[str, Path] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    conditions: dict = field(default_factory=dict)


class DoseEngine(Protocol):
    name: str

    def describe(self) -> dict:
        """Version, hashes and fixed model options for provenance."""

    def run(self, requests: list[FlightRequest], run_dir: Path) -> list[FlightResult]:
        ...
