"""Hypothetical annual calendars.

APPROXIMATION: the annual dose is the representative per-leg dose repeated
over the calendar. It does not simulate the solar and geomagnetic conditions
of each individual flight of the year. A leg is one one-way flight; a rotation
(out and back) is two legs. Calendars are hypothetical and are not claimed to
comply with any duty-time or operational limit.
"""

from __future__ import annotations

import pandas as pd

from .units import usv_to_msv

METHOD = "aproximación: dosis representativa por tramo × número de tramos (no simula cada vuelo)"


def representative_legs(summary: pd.DataFrame, profile: str, duration: str, quantity: str = "E_ICRP103") -> pd.DataFrame:
    """Per-leg dose per route and date: mean of the two directions (legs alternate out/in)."""
    s = summary[
        (summary["profile"] == profile)
        & (summary["duration"] == duration)
        & (summary["quantity"] == quantity)
        & (summary["sampling_min"] == 5.0)
    ]
    g = s.groupby(["route", "date"]).agg(
        leg_dose_uSv=("total_dose", "mean"),
        leg_hours=("airborne_h", "mean"),
        n_directions=("direction", "nunique"),
    )
    return g[g["n_directions"] == 2].reset_index()  # a representative leg needs both directions



def directional_legs(summary: pd.DataFrame, profile: str, duration: str, quantity: str = "E_ICRP103") -> pd.DataFrame:
    """Per-leg dose per route, direction and date, keyed "ROUTE direction" (e.g. "SCL-SYD inbound")."""
    s = summary[
        (summary["profile"] == profile)
        & (summary["duration"] == duration)
        & (summary["quantity"] == quantity)
        & (summary["sampling_min"] == 5.0)
    ]
    g = s.groupby(["route", "direction", "date"]).agg(leg_dose_uSv=("total_dose", "mean"), leg_hours=("airborne_h", "mean"))
    g = g.reset_index()
    g["route"] = g["route"] + " " + g["direction"]
    return g.drop(columns="direction")


def annual_table(summary: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    prof, dur = cfg["representative"]["profile"], cfg["representative"]["duration"]
    rep = representative_legs(summary, prof, dur)
    months = int(cfg["months"])
    rows = []
    for r in rep.itertuples(index=False):
        for n in cfg["legs_per_month"]:
            legs = n * months
            rows.append(
                {
                    "calendar": f"{r.route} {n} tramos/mes",
                    "kind": "ruta única",
                    "routes": r.route,
                    "date": r.date,
                    "legs_per_month": n,
                    "months": months,
                    "legs_total": legs,
                    "rotations_equivalent": legs / 2,
                    "annual_hours": legs * r.leg_hours,
                    "annual_dose_uSv": legs * r.leg_dose_uSv,
                    "annual_dose_mSv": float(usv_to_msv(legs * r.leg_dose_uSv)),
                    "method": METHOD,
                }
            )
    # Mixed calendars: a key "ROUTE" uses the mean of both directions; "ROUTE direction" uses that direction only.
    legs_table = pd.concat([rep.drop(columns="n_directions"), directional_legs(summary, prof, dur)])
    for mix in cfg.get("mixed_calendars", []):
        for date, grp in legs_table.groupby("date"):
            by_route = grp.set_index("route")
            if not set(mix["legs_per_month"]) <= set(by_route.index):
                continue
            legs = {k: int(v) * months for k, v in mix["legs_per_month"].items()}
            dose = sum(legs[k] * by_route.loc[k, "leg_dose_uSv"] for k in legs)
            hours = sum(legs[k] * by_route.loc[k, "leg_hours"] for k in legs)
            rows.append(
                {
                    "calendar": mix["name"],
                    "kind": mix.get("kind", "mixto"),
                    "routes": " + ".join(f"{k}×{v}/mes" for k, v in mix["legs_per_month"].items()),
                    "date": date,
                    "legs_per_month": sum(int(v) for v in mix["legs_per_month"].values()),
                    "months": months,
                    "legs_total": sum(legs.values()),
                    "rotations_equivalent": sum(legs.values()) / 2,
                    "annual_hours": hours,
                    "annual_dose_uSv": dose,
                    "annual_dose_mSv": float(usv_to_msv(dose)),
                    "method": METHOD,
                }
            )
    return pd.DataFrame(rows)
