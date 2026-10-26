"""Airport table with provenance (see data/airports/provenance.json)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

DEFAULT_DIR = Path(__file__).resolve().parents[2] / "data" / "airports"


@dataclass(frozen=True)
class Airport:
    icao: str
    iata: str
    name: str
    lat: float
    lon: float
    elevation_ft: float


def load_airports(directory: Path = DEFAULT_DIR) -> tuple[dict[str, Airport], dict]:
    df = pd.read_csv(directory / "airports.csv", dtype={"iata": str})
    airports = {
        r.icao: Airport(r.icao, r.iata, r.name, float(r.latitude_deg), float(r.longitude_deg), float(r.elevation_ft))
        for r in df.itertuples()
    }
    provenance = json.loads((directory / "provenance.json").read_text())
    return airports, provenance
