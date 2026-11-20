import zipfile

import numpy as np
import pandas as pd
import pytest

from pycoastkit import cli
from pycoastkit import hasaki


def line(year, month, day, hour, flag, n, values, direction):
    """One record in FORMAT(I4,3I2,2I6,4(F6.2,F6.1),I6)."""
    pairs = "".join(f"{h:6.2f}{t:6.1f}" for h, t in values)
    return f"{year:4d}{month:2d}{day:2d}{hour:2d}{flag:6d}{n:6d}{pairs}{direction:6d}"


def write_file(path):
    good = [(0.8, 6.0), (1.3, 8.0), (1.6, 8.5), (2.0, 7.0)]
    rows = [
        line(1995, 1, 1, 0, 0, 150, good, 75),
        line(1995, 1, 1, 2, 9999, 9999, [(99.99, 999.9)] * 4, 9999),
        line(1995, 1, 1, 4, 0, 150, [(0.1, 4.0), (0.2, 5.0), (0.3, 5.0), (0.4, 5.0)], 6666),
        line(1995, 1, 1, 6, 0, 150, [(20.0, 6.0), (30.0, 8.0), (31.0, 8.5), (35.0, 7.0)], 80),
        line(1995, 1, 1, 8, 77, 9999, [(99.99, 999.9), (77.77, 777.7), (99.99, 999.9),
                                       (77.77, 777.7)], 9999),
    ]
    path.write_bytes(("207  Kashima\r\n" + "\r\n".join(rows) + "\r\n").encode("shift_jis"))
    return path


def test_read_and_qc(tmp_path):
    path = write_file(tmp_path / "h2070.095.txt")
    raw = hasaki.read_nowphas(path)
    assert list(raw.index) == list(pd.date_range("1995-01-01", periods=5, freq="2h"))
    assert raw.loc["1995-01-01 00:00", "hs"] == 1.3

    clean, report = hasaki.qc_nowphas(raw)
    assert clean.loc["1995-01-01 00:00", "direction"] == 75
    assert clean.loc["1995-01-01 02:00"].drop(["calm"]).isna().all()
    assert clean.loc["1995-01-01 04:00", "calm"] and np.isnan(clean.loc["1995-01-01 04:00", "direction"])
    assert np.isnan(clean.loc["1995-01-01 06:00", "hs"])  # 30 m is unrealistic
    assert np.isnan(clean.loc["1995-01-01 08:00", "hs"])  # 77.77 code
    assert report.loc["records", "count"] == 5


def test_read_zip_and_folder(tmp_path):
    text = write_file(tmp_path / "H2070.095.txt").read_bytes()
    with zipfile.ZipFile(tmp_path / "nowphas.zip", "w") as archive:
        archive.writestr("DATA_LIST.txt", "list")
        archive.writestr("H2070.095.txt", text)
    assert len(hasaki.read_nowphas(tmp_path / "nowphas.zip")) == 5
    assert len(hasaki.read_nowphas(tmp_path)) == 5  # folder: txt + zip, duplicates dropped


def test_hors_profiles_and_beach_state(tmp_path):
    x = np.arange(-115, 386, 5)
    rows = []
    for day, shore in enumerate([60.0, 55.0, 50.0]):
        z_cm = (1.25 - 0.02 * (x - shore)) * 100
        rows.append({"date": f"2001-01-0{day + 1}", **{f"{v}m": z for v, z in zip(x, z_cm)}})
    pd.DataFrame(rows).to_csv(tmp_path / "profiles.csv", index=False)

    profiles = hasaki.read_hors_profiles(tmp_path / "profiles.csv")
    assert profiles.columns[0] == -115.0
    assert profiles.iloc[0, 0] == pytest.approx(1.25 + 0.02 * 175)
    state = hasaki.hasaki_beach_state(profiles)
    assert np.allclose(state["shoreline"], [60, 55, 50], atol=0.5)
    assert state["volume"].iloc[0] > state["volume"].iloc[2]


def test_cli_qc_then_storms(tmp_path, capsys):
    write_file(tmp_path / "h2070.095.txt")
    cli.main(["hasaki", "qc", str(tmp_path / "h2070.095.txt"), "-o", str(tmp_path / "w.csv")])
    cli.main(["storms", str(tmp_path / "w.csv")])
    assert "0 storms" in capsys.readouterr().out


def test_download_rejects_bad_interval(tmp_path):
    with pytest.raises(ValueError):
        hasaki.download_nowphas(2010, tmp_path, interval="1h")
