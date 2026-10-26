"""Extract the study airports from OurAirports and record provenance.

Usage: uv run python scripts/fetch_airports.py [--icao SCEL YMML ...]
Writes data/airports/airports.csv and data/airports/provenance.json.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
LICENSE_URL = "https://ourairports.com/data/"
ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--icao", nargs="+", default=["SCEL", "YMML", "YSSY", "NZAA", "SCCI"])
    args = ap.parse_args()

    with urllib.request.urlopen(URL, timeout=60) as resp:
        raw = resp.read()
    sha = hashlib.sha256(raw).hexdigest()
    rows = {r["ident"]: r for r in csv.DictReader(io.StringIO(raw.decode("utf-8")))}

    out_dir = ROOT / "data" / "airports"
    out_dir.mkdir(parents=True, exist_ok=True)
    fields = ["icao", "iata", "name", "municipality", "latitude_deg", "longitude_deg", "elevation_ft", "source_id"]
    with open(out_dir / "airports.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for code in args.icao:
            r = rows[code]
            w.writerow(
                {
                    "icao": r["ident"],
                    "iata": r["iata_code"],
                    "name": r["name"],
                    "municipality": r["municipality"],
                    "latitude_deg": r["latitude_deg"],
                    "longitude_deg": r["longitude_deg"],
                    "elevation_ft": r["elevation_ft"],
                    "source_id": r["id"],
                }
            )
    prov = {
        "source": "OurAirports",
        "url": URL,
        "license": "Public Domain (\"All data is released to the Public Domain\")",
        "license_url": LICENSE_URL,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_file_sha256": sha,
        "datum": "WGS84 (geographic coordinates, decimal degrees)",
        "elevation": "field elevation in feet above mean sea level",
        "icao": args.icao,
    }
    (out_dir / "provenance.json").write_text(json.dumps(prov, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {len(args.icao)} airports; source sha256={sha}")


if __name__ == "__main__":
    main()
