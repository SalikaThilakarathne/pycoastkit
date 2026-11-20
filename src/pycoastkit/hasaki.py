"""Hasaki coast, Japan: offshore waves (NOWPHAS Kashima) and beach profiles (HORS).

Waves
    The Japanese wave network NOWPHAS (MLIT / PARI) publishes 2-hourly wave
    statistics for the Kashima station (code 207), the wave record used for
    the Hasaki beach. :func:`download_nowphas` fetches yearly files,
    :func:`read_nowphas` parses them and :func:`qc_nowphas` cleans them.

    Terms: free to reuse. Cite "Nationwide Ocean Wave information network for
    Ports and HArbourS (NOWPHAS), MLIT Japan" with the page URL, state any
    processing, and for papers write that the data were observed by the MLIT
    Ports and Harbours Bureau and processed by PARI. NOWPHAS asks users not to
    harvest data automatically on a schedule - download once and keep the files.

Beach profiles
    The Hasaki Oceanographical Research Station (HORS, PARI) has surveyed a
    cross-shore profile along its pier from -115 m to +385 m every 5 m, on
    weekdays from 1986 to March 2011 and weekly since (Banno et al. 2020,
    J. Mar. Sci. Eng. 8, 871). Request or download the data from PARI
    (:data:`HORS_DATA_PAGE`) and read it with :func:`read_hors_profiles`.
    Elevations refer to the Hasaki Port datum (MHWS 1.25 m, MSL 0.65 m).
"""

from __future__ import annotations

import io
import re
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from .beach import _with_numeric_columns, beach_volume, smooth_profiles
from .shoreline import shoreline_positions

__all__ = [
    "KASHIMA_STATION",
    "HORS_DATA_PAGE",
    "NOWPHAS_PAGE",
    "HASAKI_MHWS_M",
    "HASAKI_MSL_M",
    "download_nowphas",
    "read_nowphas",
    "qc_nowphas",
    "read_hors_profiles",
    "hasaki_beach_state",
]

KASHIMA_STATION = "207"
NOWPHAS_PAGE = "https://nowphas.mlit.go.jp/pastdata/"
_NOWPHAS_DOWNLOAD = "https://nowphas.mlit.go.jp/pastdata_exe_confirmdownload"
HORS_DATA_PAGE = "https://pari.mpat.go.jp/bdhome/"
#: Mean high water springs and mean sea level at Hasaki [m, Hasaki Port datum]
HASAKI_MHWS_M = 1.25
HASAKI_MSL_M = 0.65

# FORMAT(I4,3I2,2I6,4(F6.2,F6.1),I6) for 2-hourly files; 20-min files add a minute I2
_WAVE_COLUMNS = ["flag", "n_waves", "h_mean", "t_mean", "hs", "ts", "h_1_10", "t_1_10",
                 "hmax", "tmax", "direction"]
_WIDTHS_2H = [4, 2, 2, 2] + [6] * 11
_WIDTHS_20MIN = [4, 2, 2, 2, 2] + [6] * 11


# ---------------------------------------------------------------- download

def download_nowphas(years, folder, station: str = KASHIMA_STATION, interval: str = "2h",
                     pause_s: float = 3.0, overwrite: bool = False,
                     skip_missing: bool = True) -> list[Path]:
    """Download yearly NOWPHAS wave files into ``folder`` (one request per year).

    Parameters
    ----------
    years : int or iterable of int
        Years to fetch (Kashima 2-hourly: 1972-1982, 1984-2008, 2010-2024).
    folder : path
        Where the text files are saved. Years already present are skipped,
        so the call can be repeated safely.
    station : str
        NOWPHAS station code (``"207"`` = Kashima, offshore of Hasaki).
    interval : {"2h", "20min"}
        2-hourly statistics (long record) or 20-minute statistics (2005+).
    pause_s : float
        Pause between requests, to be gentle with the server.
    skip_missing : bool
        Skip years without data (with a message) instead of raising an error.

    Returns
    -------
    list of Path
        The data files, ready for :func:`read_nowphas`.

    Notes
    -----
    This uses the same request as the download form on the NOWPHAS website.
    If the website changes, download the yearly zip files by hand from
    :data:`NOWPHAS_PAGE` and pass them to :func:`read_nowphas` directly.
    """
    if interval not in ("2h", "20min"):
        raise ValueError("interval must be '2h' or '20min'")
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    years = [int(years)] if np.isscalar(years) else [int(y) for y in years]
    kind = "2hr" if interval == "2h" else "20min"
    letter = "0" if interval == "2h" else "e"
    saved = []

    for number, year in enumerate(years):
        name = f"h{station}{letter}.{year % 100:03d}.txt"  # e.g. h2070.095.txt for 1995
        target = folder / name
        if target.exists() and not overwrite:
            saved.append(target)
            continue
        if number:
            time.sleep(pause_s)
        payload = urllib.parse.urlencode({
            "start_yy": year,
            "end_yy": year,
            "checkedvtxt": f"{station}_{kind}_txt,",
            "code_list": "undefined",
            "code_map": "undefined",
        }).encode()
        request = urllib.request.Request(
            _NOWPHAS_DOWNLOAD, data=payload,
            headers={"User-Agent": "pycoastkit (Python package)"},
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            content = response.read()
        member = None
        if zipfile.is_zipfile(io.BytesIO(content)):
            archive = zipfile.ZipFile(io.BytesIO(content))
            member = next((m for m in archive.namelist()
                           if Path(m).name.lower() == name.lower()), None)
        if member is None:
            message = (f"no {interval} data for station {station} in {year} "
                       f"(see {NOWPHAS_PAGE} for available years)")
            if not skip_missing:
                raise RuntimeError(message)
            print(f"skipped {year}: {message}")
            continue
        target.write_bytes(archive.read(member))
        saved.append(target)
        print(f"downloaded {name}")
    return saved


# ---------------------------------------------------------------- waves

def _read_lines(source) -> list[tuple[str, str]]:
    """Return (name, text) pairs from a text file, a zip, or a folder."""
    source = Path(source)
    if source.is_dir():
        pairs = []
        for path in sorted(source.iterdir()):
            if path.suffix.lower() in (".txt", ".zip"):
                pairs.extend(_read_lines(path))
        return pairs
    if source.suffix.lower() == ".zip":
        with zipfile.ZipFile(source) as archive:
            return [(Path(m).name, archive.read(m).decode("shift_jis", errors="replace"))
                    for m in archive.namelist()
                    if re.match(r"h\d{3}[0e]\.\d{3}\.txt$", Path(m).name, re.IGNORECASE)]
    return [(source.name, source.read_bytes().decode("shift_jis", errors="replace"))]


def read_nowphas(sources) -> pd.DataFrame:
    """Read NOWPHAS wave-statistics files (``.txt``, the downloaded ``.zip``, or a folder).

    Returns the raw values (including missing-value codes such as 99.99) with
    a ``time`` index and the columns ``flag, n_waves, h_mean, t_mean, hs, ts,
    h_1_10, t_1_10, hmax, tmax, direction``:

    * ``h_mean``/``t_mean`` - mean wave height [m] / period [s]
    * ``hs``/``ts`` - significant wave (H1/3, T1/3)
    * ``h_1_10``/``t_1_10`` - highest one-tenth waves
    * ``hmax``/``tmax`` - highest wave
    * ``direction`` - degrees clockwise from true north (waves coming from)

    Pass the result to :func:`qc_nowphas` before analysis.
    """
    if isinstance(sources, (str, Path)):
        sources = [sources]
    frames = []
    for source in sources:
        for name, text in _read_lines(source):
            lines = [line for line in text.splitlines()[1:] if line.strip()]
            if not lines:
                continue
            twenty_min = name.lower()[4] == "e"
            widths = _WIDTHS_20MIN if twenty_min else _WIDTHS_2H
            time_cols = ["year", "month", "day", "hour"] + (["minute"] if twenty_min else [])
            table = pd.read_fwf(io.StringIO("\n".join(lines)), widths=widths, header=None,
                                names=time_cols + _WAVE_COLUMNS)
            table.index = pd.to_datetime(table[time_cols])
            frames.append(table.drop(columns=time_cols))
    if not frames:
        raise FileNotFoundError("no NOWPHAS wave files found")
    data = pd.concat(frames).sort_index()
    data = data[~data.index.duplicated(keep="last")]
    data.index.name = "time"
    return data


def qc_nowphas(raw: pd.DataFrame, max_hs: float = 25.0, calm_hs: float = 0.25):
    """Clean NOWPHAS wave statistics.

    Steps
    -----
    1. Missing codes (9999, 99.99, 999.9) and the special codes for calm
       (66.66, 666.6, flag 66) and "not a high wave" (77.77, 777.7) -> NaN.
    2. Records flagged missing (flag 9999) -> all values NaN.
    3. Unrealistic ``hs > max_hs`` -> NaN for that record's heights/periods.
    4. Direction code 6666 (calm, used until 1999) -> NaN; from 2000 on,
       NOWPHAS lists a direction even in calm seas, so direction is also set
       to NaN when ``hs <= calm_hs``. A boolean ``calm`` column records both.

    Returns
    -------
    clean : pandas.DataFrame
        Same columns as the input plus ``calm``; values are floats.
    report : pandas.DataFrame
        Number of values changed per step and column.
    """
    data = raw.copy()
    flag = data["flag"]
    values = data.drop(columns=["flag"]).astype(float)
    heights = ["h_mean", "hs", "h_1_10", "hmax"]
    periods = ["t_mean", "ts", "t_1_10", "tmax"]
    report = {}

    def count(name, mask):
        report[name] = int(np.asarray(mask).sum())

    codes = pd.DataFrame(False, index=values.index, columns=values.columns)
    codes[heights] = values[heights].isin([99.99, 66.66, 77.77])
    codes[periods] = values[periods].isin([999.9, 666.6, 777.7])
    codes[["n_waves", "direction"]] = values[["n_waves", "direction"]].eq(9999)
    count("missing or special code", codes)
    values = values.mask(codes)

    missing_flag = flag.eq(9999)
    count("flag 9999 (whole record)", values[missing_flag].notna())
    values.loc[missing_flag] = np.nan

    too_high = values["hs"] > max_hs
    count(f"hs > {max_hs} m", values.loc[too_high, heights + periods].notna())
    values.loc[too_high, heights + periods] = np.nan

    calm_code = values["direction"].eq(6666)
    calm = calm_code | flag.eq(66) | (values["hs"] <= calm_hs)
    count("direction set to NaN (calm)", calm & values["direction"].notna())
    values.loc[calm, "direction"] = np.nan

    clean = values
    clean.insert(0, "flag", flag.where(~missing_flag))
    clean["calm"] = calm
    report["records"] = len(clean)
    report["records with valid hs"] = int(clean["hs"].notna().sum())
    return clean, pd.Series(report, name="count").to_frame()


# ---------------------------------------------------------------- beach profiles

def read_hors_profiles(path, units: str = "cm", date_column: str = "date") -> pd.DataFrame:
    """Read HORS beach profiles from a CSV table.

    Expected layout: one row per survey, a ``date`` column, and one column per
    cross-shore position (``-115m, -110m, ..., 385m`` or plain numbers).
    Elevations are converted to metres when ``units="cm"``.

    Returns a profile table (DatetimeIndex, float columns = positions in m)
    for the :mod:`pycoastkit.beach` functions.
    """
    table = pd.read_csv(path)
    if date_column not in table.columns:
        raise KeyError(f"column {date_column!r} not found; columns start with "
                       f"{list(table.columns[:3])}")
    table.index = pd.to_datetime(table.pop(date_column))
    table = table.apply(pd.to_numeric, errors="coerce")
    if units == "cm":
        table = table / 100.0
    elif units != "m":
        raise ValueError("units must be 'cm' or 'm'")

    return _with_numeric_columns(table)


def hasaki_beach_state(profiles: pd.DataFrame, water_level: float = HASAKI_MHWS_M,
                       sigma: float = 2.0, volume_zone=(-40.0, 60.0)) -> pd.DataFrame:
    """Daily shoreline position and beach volume from HORS profiles.

    Profiles are smoothed (Gaussian, ``sigma`` grid points) to suppress survey
    noise, the shoreline is the seaward crossing of ``water_level``
    (default MHWS, 1.25 m) and the volume is integrated over ``volume_zone``
    [m] above the lowest surveyed bed at each position.

    Returns a DataFrame with ``shoreline`` [m] and ``volume`` [m³/m].
    """
    smooth = smooth_profiles(profiles, sigma=sigma)
    return pd.DataFrame({
        "shoreline": shoreline_positions(smooth, water_level),
        "volume": beach_volume(smooth, *volume_zone),
    })


# ---------------------------------------------------------------- command line

def add_cli(subparsers) -> None:
    p = subparsers.add_parser("hasaki", help="download and quality-control Hasaki wave data")
    hs = p.add_subparsers(dest="hasaki_command", required=True)

    d = hs.add_parser("download", help="download NOWPHAS Kashima wave files")
    d.add_argument("years", help="a year or a range, e.g. 2010 or 1987-2022")
    d.add_argument("-d", "--folder", default="nowphas_kashima")
    d.add_argument("--interval", choices=["2h", "20min"], default="2h")
    d.set_defaults(func=_cli_download)

    q = hs.add_parser("qc", help="read + QC NOWPHAS files and save a clean wave table")
    q.add_argument("sources", nargs="+", help="text files, zip files or folders")
    q.add_argument("-o", "--output", default="hasaki_waves.csv",
                   help="output .csv or .parquet")
    q.set_defaults(func=_cli_qc)


def _years(text: str) -> list[int]:
    if "-" in text:
        first, last = (int(part) for part in text.split("-"))
        return list(range(first, last + 1))
    return [int(text)]


def _cli_download(args) -> None:
    files = download_nowphas(_years(args.years), args.folder, interval=args.interval)
    print(f"{len(files)} file(s) in {Path(args.folder).name}")


def _cli_qc(args) -> None:
    clean, report = qc_nowphas(read_nowphas(args.sources))
    out = Path(args.output)
    if out.suffix.lower() == ".parquet":
        clean.to_parquet(out)
    else:
        clean.to_csv(out)
    print(report.to_string())
    print(f"saved {len(clean):,} records to {out.name}")
