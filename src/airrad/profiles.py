"""Vertical flight profiles (pressure altitude vs. time).

All profiles are *assumptions* defined in configuration. They are not
validated operational profiles for any specific aircraft type. Altitudes are
ISA pressure altitude in feet (flight level x 100). Field elevations are used as
the pressure altitude at departure/arrival (standard-atmosphere assumption).

Breakpoints are rounded to whole minutes because CARI-7 DEG waypoints carry
integer minutes; any rounding is reported as a warning.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class AltitudeProfile:
    name: str
    kind: str  # "constant" | "step"
    levels_fl: tuple[int, ...]
    climb_min: int
    descent_min: int
    cruise_fractions: tuple[float, ...] | None = None
    step_climb_fpm: float | None = None
    note: str = ""
    extra: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.kind not in ("constant", "step"):
            raise ValueError(f"Perfil {self.name}: tipo desconocido {self.kind!r}")
        if self.climb_min <= 0 or self.descent_min <= 0:
            raise ValueError(f"Perfil {self.name}: ascenso y descenso deben durar > 0 min")
        if self.kind == "constant" and len(self.levels_fl) != 1:
            raise ValueError(f"Perfil {self.name}: crucero constante requiere un único nivel")
        if self.kind == "step":
            if len(self.levels_fl) < 2:
                raise ValueError(f"Perfil {self.name}: el escalonado requiere al menos dos niveles")
            if self.cruise_fractions is None or len(self.cruise_fractions) != len(self.levels_fl):
                raise ValueError(f"Perfil {self.name}: indique una fracción de crucero por nivel")
            if not np.isclose(sum(self.cruise_fractions), 1.0):
                raise ValueError(f"Perfil {self.name}: las fracciones de crucero deben sumar 1")
            if any(f <= 0 for f in self.cruise_fractions):
                raise ValueError(f"Perfil {self.name}: fracciones de crucero deben ser > 0")
            if not self.step_climb_fpm or self.step_climb_fpm <= 0:
                raise ValueError(f"Perfil {self.name}: step_climb_fpm debe ser > 0")

    @classmethod
    def from_config(cls, name: str, cfg: dict) -> "AltitudeProfile":
        kind = cfg["type"]
        levels = (int(cfg["cruise_fl"]),) if kind == "constant" else tuple(int(x) for x in cfg["levels_fl"])
        fr = cfg.get("cruise_fractions")
        return cls(
            name=name,
            kind=kind,
            levels_fl=levels,
            climb_min=int(cfg["climb_min"]),
            descent_min=int(cfg["descent_min"]),
            cruise_fractions=tuple(float(x) for x in fr) if fr is not None else None,
            step_climb_fpm=float(cfg["step_climb_fpm"]) if "step_climb_fpm" in cfg else None,
            note=cfg.get("note", ""),
        )

    def breakpoints(
        self, airborne_min: int, origin_elev_ft: float, dest_elev_ft: float
    ) -> tuple[np.ndarray, np.ndarray, list[str]]:
        """Piecewise-linear (t_min, pressure_altitude_ft) knots of the profile."""
        warnings: list[str] = []
        T = float(airborne_min)
        levels_ft = [fl * 100.0 for fl in self.levels_fl]
        if self.kind == "constant":
            t = [0.0, self.climb_min, T - self.descent_min, T]
            a = [origin_elev_ft, levels_ft[0], levels_ft[0], dest_elev_ft]
        else:
            step_min = [abs(b - a) / self.step_climb_fpm for a, b in zip(levels_ft[:-1], levels_ft[1:])]
            level_time = T - self.climb_min - self.descent_min - sum(step_min)
            if level_time <= 0:
                raise ValueError(f"Perfil {self.name}: duración {airborne_min} min insuficiente")
            t, a = [0.0, float(self.climb_min)], [origin_elev_ft, levels_ft[0]]
            for i, lvl in enumerate(levels_ft):
                t.append(t[-1] + level_time * self.cruise_fractions[i])
                a.append(lvl)
                if i < len(step_min):
                    t.append(t[-1] + step_min[i])
                    a.append(levels_ft[i + 1])
            t[-1] = T - self.descent_min  # remove float drift on the last cruise point
            t.append(T)
            a.append(dest_elev_ft)
        t_arr = np.asarray(t, dtype=float)
        if t_arr[1] >= t_arr[-2]:
            raise ValueError(f"Perfil {self.name}: ascenso+descenso exceden la duración {airborne_min} min")
        rounded = np.round(t_arr)
        if np.any(np.abs(rounded - t_arr) > 1e-9):
            warnings.append(
                f"Perfil {self.name}: tiempos de quiebre redondeados a minutos enteros "
                f"(máx. {np.max(np.abs(rounded - t_arr)):.2f} min) por el formato DEG de CARI."
            )
        if np.any(np.diff(rounded) <= 0):
            raise ValueError(f"Perfil {self.name}: quiebres no estrictamente crecientes tras redondeo")
        return rounded, np.asarray(a, dtype=float), warnings
