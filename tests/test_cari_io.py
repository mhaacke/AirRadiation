"""CARI-7 file formats. Parser tests use SYNTHETIC fixtures (see tests/fixtures/README.md)."""

import shutil
from pathlib import Path

import numpy as np
import pytest

from airrad.engines.cari7 import (
    Cari7Config,
    Cari7Engine,
    CariError,
    format_deg_coord,
    parse_dat,
    parse_sum,
    write_deg,
)

FIX = Path(__file__).parent / "fixtures"
ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "third_party" / "cari7" / "CARI_7_DVD"


def test_deg_coordinates():
    assert format_deg_coord(-33.393, "N", "S") == (33, "23.5800", "S")
    assert format_deg_coord(144.8379, "E", "W") == (144, "50.2740", "E")
    assert format_deg_coord(-0.25, "N", "S") == (0, "15.0000", "S")
    # rounding never produces 60 minutes
    assert format_deg_coord(10.9999999999, "N", "S") == (11, "0.0000", "N")
    assert format_deg_coord(-179.99999, "E", "W")[0] == 179


def test_write_deg_format_and_limits(tmp_path):
    f = tmp_path / "S0000.DEG"
    write_deg(f, "SCL-MEL test", 2020, 2, [0, 5, 10], [-33.393, -34.0, -35.0], [-70.786, -71.0, 179.5], [1555, 20000, 37000])
    lines = f.read_text().splitlines()
    assert lines[0] == "02/2020, SCL-MEL_test"
    assert lines[2] == "33, 23.5800, S, 70, 47.1600, W, 1555, 0"
    assert lines[4].endswith("E, 37000, 10")
    with pytest.raises(CariError):
        write_deg(f, "x", 2020, 2, [1, 5], [0, 0], [0, 0], [0, 0])  # must start at minute 0
    with pytest.raises(CariError):
        write_deg(f, "x", 2020, 2, [0, 2001], [0, 0], [0, 0], [0, 0])  # 2000-minute limit
    with pytest.raises(CariError):
        write_deg(f, "x", 2020, 2, [0, 2.5], [0, 0], [0, 0], [0, 0])  # integer minutes only


def test_parse_synthetic_sum_and_dat():
    s = parse_sum(FIX / "SYNTH.SUM")
    assert s["total"] == pytest.approx(0.12)
    assert s["unit_raw"] == "microSv"
    assert s["quantity_label"] == "ICRP Pub. 103 EFFECTIVE DOSE"
    assert s["date"] == "2020/02/00" and s["gcr_model"] == 4
    d = parse_dat(FIX / "SYNTH.DAT")
    assert len(d) == 3
    assert d["lon"].tolist() == pytest.approx([179.9, -179.9, -179.7])  # 0..360 east -> [-180, 180)
    assert d["t_mid_min"].tolist() == [0.5, 1.5, 2.5]
    # .DAT cumulative column is already a dose: compare, never integrate it again
    assert (d["rate"] / 60).sum() == pytest.approx(d["cum_dose"].iloc[-1])


def test_parse_sum_reports_cari_rejection():
    with pytest.raises(CariError, match="no reportó"):
        parse_sum(FIX / "SYNTH_BAD.SUM")


def _engine():
    if not (INSTALL / "cari-7_linux_intel_exe").exists():
        pytest.skip("CARI-7 no instalado (scripts/install_cari7.py)")
    eng = Cari7Engine(Cari7Config(install_dir=INSTALL, docker_image="debian@sha256:7ff6ba31527b9e336162fa061746c366c4b2032f4d2cff2078bea43f78efe3f8"))
    if eng.check_installation():
        pytest.skip("; ".join(eng.check_installation()))
    return eng


def test_installation_metadata():
    eng = _engine()
    d = eng.describe()
    assert d["executable_arch"] == "x86-64"
    assert eng.heliocentric_potential(2020, 2) == 254
    assert eng.heliocentric_potential(2024, 10) == 1040


@pytest.mark.cari
def test_official_example_reproduced(tmp_path):
    eng = _engine()
    if shutil.which("docker") is None:
        pytest.skip("docker no disponible")
    work = Path.home() / ".cache" / "airrad_pytest" / tmp_path.name  # under $HOME for Colima mounts
    try:
        res = eng.run_official_example(work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    assert res["identical"], res
    assert res["computed_total_uSv"] == pytest.approx(0.50704)
    assert np.isclose(res["parser_rate_integral_uSv"], 0.50704, rtol=1e-4)
