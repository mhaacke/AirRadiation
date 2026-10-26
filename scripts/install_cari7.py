"""Download and unpack the official FAA CARI-7 package.

The package is not redistributed with this repository. This script downloads
it from the FAA, checks its SHA-256 and unpacks it into third_party/cari7/.

The FAA republishes the same file name when it refreshes the monthly data
(heliocentric potentials, Forbush and Kp files), so the hash is expected to
change over time. A mismatch with the hash this study was run with stops the
installation unless --accept-hash is given; the hash actually installed is
always recorded in third_party/cari7/INSTALL_PROVENANCE.json.

Usage:
  uv run python scripts/install_cari7.py
  uv run python scripts/install_cari7.py --zip /path/to/cari_7exe.zip
  uv run python scripts/install_cari7.py --accept-hash <sha256>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import stat
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "third_party" / "cari7"
PAGE = "https://www.faa.gov/data_research/research/med_humanfacs/aeromedical/radiobiology/cari7"
URL = "https://www.faa.gov/sites/faa.gov/files/data_research/research/med_humanfacs/aeromedical/cari_7exe.zip"
# Package used for the results in this repository (downloaded 2026-10-25).
STUDY_SHA256 = "a20d9ca8aec142337be52632fbe6f251545d771bdfc0e6bbb69e7a4ddfc94197"
LINUX_EXE = "CARI_7_DVD/cari-7_linux_intel_exe"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", type=Path, help="use an already downloaded cari_7exe.zip")
    ap.add_argument("--accept-hash", help="accept a package whose SHA-256 differs from the study's")
    ap.add_argument("--force", action="store_true", help="replace an existing installation")
    args = ap.parse_args()

    DEST.mkdir(parents=True, exist_ok=True)
    target = DEST / "CARI_7_DVD"
    if target.exists() and not args.force:
        raise SystemExit(f"{target} ya existe; use --force para reinstalar")

    zpath = args.zip
    if zpath is None:
        zpath = DEST / "cari_7exe.zip"
        print(f"Descargando {URL}")
        req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (airrad installer)"})
        with urllib.request.urlopen(req, timeout=300) as resp, open(zpath, "wb") as fh:
            shutil.copyfileobj(resp, fh)
    digest = sha256(zpath)
    print(f"SHA-256 {digest}")
    if digest != STUDY_SHA256 and digest != args.accept_hash:
        raise SystemExit(
            "El paquete difiere del usado en este estudio (la FAA actualiza los datos mensualmente).\n"
            f"  estudio: {STUDY_SHA256}\n  actual:  {digest}\n"
            "Si desea continuar con el paquete actual, repita con --accept-hash " + digest
        )

    with zipfile.ZipFile(zpath) as zf:
        for name in zf.namelist():  # refuse path traversal
            if name.startswith("/") or ".." in Path(name).parts:
                raise SystemExit(f"Entrada sospechosa en el zip: {name}")
        if target.exists():
            shutil.rmtree(target)
        zf.extractall(DEST)
    exe = DEST / LINUX_EXE
    exe.chmod(exe.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    prov = {
        "package_url": URL,
        "documentation_page": PAGE,
        "package_sha256": digest,
        "matches_study_package": digest == STUDY_SHA256,
        "installed_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "linux_executable": LINUX_EXE,
        "linux_executable_sha256": sha256(exe),
        "terms": (
            "Software y documentación difundidos por el U.S. DOT/FAA 'in the interest of information exchange'; "
            "el Gobierno de EE.UU. no asume responsabilidad (HELP.TXT). El paquete no declara una licencia de "
            "redistribución para binarios y datos, por lo que este repositorio no los incluye."
        ),
    }
    (DEST / "INSTALL_PROVENANCE.json").write_text(json.dumps(prov, indent=2, ensure_ascii=False) + "\n")
    print(f"Instalado en {target}")


if __name__ == "__main__":
    main()
