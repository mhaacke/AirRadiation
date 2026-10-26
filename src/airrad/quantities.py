"""Dosimetric quantities.

Effective dose, ambient dose equivalent and absorbed dose are different
quantities. Effective dose and H*(10) share the unit sievert but are not
interchangeable; absorbed dose is in gray. Every result in this project carries
its quantity and arithmetic is only performed within a single quantity.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class QuantityInfo:
    key: str
    label_es: str
    dose_unit: str
    rate_unit: str
    cari_tally: int  # DEFAULT.INP line 4
    cari_label: str  # text CARI-7 writes in .SUM/.OUT files


class Quantity(Enum):
    EFFECTIVE_DOSE_ICRP103 = QuantityInfo(
        "E_ICRP103", "Dosis efectiva (ICRP 103)", "µSv", "µSv/h", 2, "ICRP Pub. 103 EFFECTIVE DOSE"
    )
    EFFECTIVE_DOSE_ICRP60 = QuantityInfo(
        "E_ICRP60", "Dosis efectiva (ICRP 60)", "µSv", "µSv/h", 3, "ICRP Pub. 60 EFFECTIVE DOSE"
    )
    AMBIENT_DOSE_EQUIVALENT = QuantityInfo(
        "H10", "Equivalente de dosis ambiental H*(10)", "µSv", "µSv/h", 4, "ICRU AMBIENT DOSE EQ. H(*10)"
    )
    ABSORBED_DOSE_WHOLE_BODY = QuantityInfo(
        "D_WB", "Dosis absorbida promedio en cuerpo entero", "µGy", "µGy/h", 5, "AVE WHOLE-BODY ABSORBED DOSE"
    )

    @property
    def info(self) -> QuantityInfo:
        return self.value

    @classmethod
    def from_key(cls, key: str) -> "Quantity":
        for q in cls:
            if q.info.key == key:
                return q
        raise ValueError(f"Magnitud desconocida {key!r}; opciones: {[q.info.key for q in cls]}")


def require_single_quantity(keys) -> str:
    """Raise if a collection mixes dosimetric quantities."""
    unique = set(keys)
    if len(unique) != 1:
        raise ValueError(f"No se pueden combinar magnitudes dosimétricas distintas: {sorted(unique)}")
    return unique.pop()
