"""Run manifest: what was run, with which inputs, code and engine."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

SOURCES = [
    {
        "what": "CARI-7 (programa, datos y documentación)",
        "url": "https://www.faa.gov/data_research/research/med_humanfacs/aeromedical/radiobiology/cari7",
    },
    {
        "what": "CARI-7 User's Guide, DOT/FAA/AM-21/6 (Copeland 2021)",
        "url": "https://www.faa.gov/sites/faa.gov/files/data_research/research/med_humanfacs/aeromedical/202106.pdf",
    },
    {
        "what": "CARI-7 Radiation Transport in the Atmosphere, DOT/FAA/AM-21/5",
        "url": "https://www.faa.gov/sites/faa.gov/files/data_research/research/med_humanfacs/aeromedical/202105.pdf",
    },
    {
        "what": "CARI-7 Geomagnetic Cutoff Rigidity Calculations and Tables for 1965-2010, DOT/FAA/AM-19/4",
        "url": "https://www.faa.gov/sites/faa.gov/files/data_research/research/med_humanfacs/aeromedical/201904.pdf",
    },
    {"what": "Coordenadas de aeropuertos: OurAirports (dominio público)", "url": "https://ourairports.com/data/"},
    {
        "what": "SILSO, Royal Observatory of Belgium: número de manchas mensual y suavizado V2.0 (justificación de fechas)",
        "url": "https://www.sidc.be/SILSO/datafiles",
    },
]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git_state(root: Path) -> dict:
    def git(*args):
        try:
            return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return None

    status = git("status", "--porcelain")
    h = hashlib.sha256()
    for sub in ("src", "config", "scripts"):
        for f in sorted((root / sub).rglob("*")):
            if f.is_file() and "__pycache__" not in f.parts:
                h.update(f.relative_to(root).as_posix().encode())
                h.update(hashlib.sha256(f.read_bytes()).digest())
    return {
        "commit": git("rev-parse", "HEAD"),
        "dirty": bool(status) if status is not None else None,
        "source_tree_sha256": h.hexdigest(),  # src/, config/, scripts/ as used for this run
    }


def environment(root: Path) -> dict:
    pkgs = {}
    for name in ("numpy", "pandas", "pyproj", "matplotlib", "cartopy", "pyyaml"):
        try:
            pkgs[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            pkgs[name] = None
    lock = root / "uv.lock"
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "packages": pkgs,
        "uv_lock_sha256": sha256_file(lock) if lock.exists() else None,
    }


def write_manifest(path: Path, **content) -> None:
    content.setdefault("created_utc", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    path.write_text(json.dumps(content, indent=2, ensure_ascii=False, default=str) + "\n")
