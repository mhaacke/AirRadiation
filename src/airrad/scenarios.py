"""Study configuration and scenario matrix."""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import yaml

from . import geodesy
from .airports import Airport, load_airports
from .profiles import AltitudeProfile
from .quantities import Quantity
from .trajectory import Trajectory, import_csv, synthesize_geodesic

DIRECTION_SHORT = {"outbound": "out", "inbound": "in"}


@dataclass
class Scenario:
    scenario_id: str
    route: str
    direction: str
    origin: str
    destination: str
    profile: str
    duration: str
    date: str
    year: int
    month: int
    quantity: Quantity
    sampling_min: float
    airborne_min: int
    blocks: list[str] = field(default_factory=list)
    imported_track: dict | None = None

    def row(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "route": self.route,
            "direction": self.direction,
            "origin": self.origin,
            "destination": self.destination,
            "profile": self.profile,
            "duration": self.duration,
            "date": self.date,
            "quantity": self.quantity.info.key,
            "sampling_min": self.sampling_min,
            "airborne_min": self.airborne_min,
            "blocks": ";".join(self.blocks),
        }


@dataclass
class Study:
    path: Path
    root: Path
    raw: dict
    airports: dict[str, Airport]
    airports_provenance: dict
    profiles: dict[str, AltitudeProfile]

    @classmethod
    def load(cls, path: str | Path) -> "Study":
        path = Path(path).resolve()
        root = path.parent.parent if path.parent.name == "config" else path.parent
        raw = yaml.safe_load(path.read_text())
        airports, prov = load_airports(root / raw["airports_dir"])
        profiles = {k: AltitudeProfile.from_config(k, v) for k, v in raw["profiles"].items()}
        return cls(path, root, raw, airports, prov, profiles)

    # ---------------------------------------------------------------- helpers
    def endpoints(self, route: str, direction: str) -> tuple[Airport, Airport]:
        r = self.raw["routes"][route]
        a, b = self.airports[r["a"]], self.airports[r["b"]]
        return (a, b) if direction == "outbound" else (b, a)

    def via(self, route: str, direction: str) -> list[tuple[float, float]] | None:
        """Intermediate waypoints in flight order, or None for the plain geodesic.

        Route option ``via: {path: CSV, order: a_to_b | b_to_a}``; the CSV has
        columns latitude_deg, longitude_deg.
        """
        v = self.raw["routes"][route].get("via")
        if not v:
            return None
        df = pd.read_csv(self.root / v["path"])
        pts = list(zip(df["latitude_deg"].astype(float), df["longitude_deg"].astype(float)))
        if v.get("order", "a_to_b") not in ("a_to_b", "b_to_a"):
            raise ValueError(f"Ruta {route}: via.order debe ser a_to_b o b_to_a")
        a_to_b = pts if v.get("order", "a_to_b") == "a_to_b" else pts[::-1]
        return a_to_b if direction == "outbound" else a_to_b[::-1]

    def path_distance_m(self, route: str, direction: str) -> float:
        o, t = self.endpoints(route, direction)
        via = self.via(route, direction) or []
        lats = [o.lat, *(p[0] for p in via), t.lat]
        lons = [o.lon, *(p[1] for p in via), t.lon]
        return float(geodesy.segment_distances_m(lats, lons).sum())

    def airborne_minutes(self, route: str, direction: str, duration: str) -> int:
        d = self.raw["durations"][duration]
        if "airborne_min" in d:
            return int(d["airborne_min"][route][direction])
        dist_m = self.path_distance_m(route, direction)
        return int(round(dist_m / 1852.0 / float(d["ground_speed_kt"]) * 60.0))

    def departure(self, date_key: str) -> pd.Timestamp:
        d = self.raw["dates"][date_key]
        day = int(self.raw["study"].get("departure_day", 15))
        hhmm = self.raw["study"].get("departure_time_utc", "00:00")
        return pd.Timestamp(f"{d['year']:04d}-{d['month']:02d}-{day:02d}T{hhmm}:00Z")

    # --------------------------------------------------------------- matrix
    def scenarios(self) -> list[Scenario]:
        default_dt = float(self.raw["study"].get("sampling_min", 5))
        out: dict[str, Scenario] = {}
        for blk in self.raw["matrix"]:
            dts = [float(x) for x in blk.get("sampling_min", [default_dt])]
            combos = itertools.product(
                blk["routes"], blk["directions"], blk["profiles"], blk["durations"], blk["dates"], blk["quantities"], dts
            )
            for route, direction, prof, dur, date_key, qkey, dt in combos:
                checks = (
                    ("ruta", route, self.raw["routes"]),
                    ("perfil", prof, self.profiles),
                    ("duración", dur, self.raw["durations"]),
                    ("fecha", date_key, self.raw["dates"]),
                )
                for name, key, coll in checks:
                    if key not in coll:
                        raise ValueError(f"Bloque {blk['block']}: {name} desconocida {key!r}")
                q = Quantity.from_key(qkey)
                o, t = self.endpoints(route, direction)
                sid = (
                    f"{route}_{DIRECTION_SHORT[direction]}_{prof}_{dur}_{date_key}_{q.info.key}_dt{dt:g}"
                )
                if sid in out:
                    out[sid].blocks.append(blk["block"])
                    continue
                d = self.raw["dates"][date_key]
                out[sid] = Scenario(
                    sid, route, direction, o.icao, t.icao, prof, dur, date_key, int(d["year"]), int(d["month"]),
                    q, dt, self.airborne_minutes(route, direction, dur), [blk["block"]],
                )  # fmt: skip
        for trk in self.raw.get("imported_tracks") or []:
            for date_key, qkey in itertools.product(trk["dates"], trk.get("quantities", ["E_ICRP103"])):
                d = self.raw["dates"][date_key]
                q = Quantity.from_key(qkey)
                sid = f"IMP_{trk['name']}_{date_key}_{q.info.key}"
                out[sid] = Scenario(
                    sid, f"IMP:{trk['name']}", "n/a", "", "", "importado", "importado", date_key,
                    int(d["year"]), int(d["month"]), q, 0.0, 0, ["importadas"], trk,
                )  # fmt: skip
        return list(out.values())

    def trajectory(self, sc: Scenario) -> Trajectory:
        if sc.imported_track is not None:
            trk = sc.imported_track
            tr = import_csv(self.root / trk["path"], trk["altitude_unit"], trk["altitude_reference"])
            sc.airborne_min = int(round(tr.duration_min))
            return tr
        o, t = self.endpoints(sc.route, sc.direction)
        tr = synthesize_geodesic(o, t, self.profiles[sc.profile], sc.airborne_min, self.departure(sc.date), sc.sampling_min,
                                 via=self.via(sc.route, sc.direction))  # fmt: skip
        tr.meta.update(route=sc.route, direction=sc.direction, date=sc.date, duration=sc.duration)
        return tr
