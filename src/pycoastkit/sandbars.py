"""Sandbars: detection and description from cross-shore profiles.

Sandbars are shore-parallel ridges of sand in the surf zone, each with a
crest and a trough on either side. They break waves offshore and so shape how
much a storm erodes the beach. Work on shoreline-relative profiles (see
:func:`pycoastkit.shoreline_relative_profiles`) so that bar distances are
measured from the shoreline.

Bar geometry
------------
::

        crest ─┐                          height = crest above the straight
       ╱‾‾‾‾‾‾╲│                                   line joining the troughs
  ____╱        ╲____                      depth  = reference level - crest
  trough        trough                    slopes = crest-to-trough gradients
  (landward)    (seaward)

The default thresholds (bars more than 50 m from the shoreline; inner zone
up to 170 m with bars higher than 0.24 m; outer zone with bars higher than
0.5 m; depth below MHWS 1.25 m) are those used for Hasaki, Japan.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks

from .beach import _with_numeric_columns

__all__ = [
    "bar_height",
    "find_sandbars",
    "sandbar_table",
    "bar_state",
    "PROFILE_TYPES",
]

#: Profile types by bar configuration (used by :func:`bar_state`)
PROFILE_TYPES = {1: "unbarred", 2: "inner bar", 3: "outer bar", 4: "inner and outer bars"}

BAR_COLUMNS = ["crest_x", "crest_z", "height", "depth", "trough_land_x", "trough_sea_x",
               "slope_land", "slope_sea", "zone"]


def bar_height(x_land, x_crest, x_sea, z_land, z_crest, z_sea):
    """Height of a crest above the straight line joining its two troughs [m]."""
    chord = z_sea + (z_land - z_sea) * (x_crest - x_sea) / (x_land - x_sea)
    return z_crest - chord


def find_sandbars(x, elevation, smooth_sigma: float = 2.0, x_range=(0.0, None),
                  reference_level: float = 1.25, min_distance: float = 50.0,
                  zone_split: float = 170.0, min_height=(0.24, 0.5),
                  keep_all: bool = False) -> pd.DataFrame:
    """Find the sandbars on one profile.

    Steps
    -----
    1. Keep positions inside ``x_range`` (default: from the shoreline seaward
       on a shoreline-relative profile) and smooth with a Gaussian filter
       (``smooth_sigma`` in grid points; 0 = no smoothing).
    2. Crests are local maxima and troughs local minima of the smoothed profile.
    3. Each crest is paired with the nearest trough on each side. If there is
       no trough seaward (the profile keeps falling), the last point is used,
       at the lower of its own elevation and the landward trough's. Crests
       without a landward trough are part of the beach face and are skipped.
    4. A bar is kept if its crest is more than ``min_distance`` from x = 0 and
       its height exceeds ``min_height[0]`` (inner zone, crest at or within
       ``zone_split``) or ``min_height[1]`` (outer zone). Use ``keep_all=True``
       to return every crest with its zone and skip this filter.

    Returns
    -------
    pandas.DataFrame
        One row per bar, landward to seaward: ``crest_x`` [m], ``crest_z`` [m],
        ``height`` [m], ``depth`` (``reference_level - crest_z``) [m],
        ``trough_land_x``, ``trough_sea_x`` [m], ``slope_land`` and
        ``slope_sea`` (crest-to-trough gradients, positive), ``zone``
        (``"inner"``/``"outer"``).
    """
    x = np.asarray(x, dtype=float)
    z = np.asarray(elevation, dtype=float)
    valid = np.isfinite(z)
    x, z = x[valid], z[valid]
    # smooth the whole profile first, then cut, to avoid edge effects at the range limits
    zs = gaussian_filter1d(z, smooth_sigma, mode="reflect") if smooth_sigma else z.copy()
    keep = np.ones_like(x, dtype=bool)
    if x_range[0] is not None:
        keep &= x >= x_range[0]
    if x_range[1] is not None:
        keep &= x <= x_range[1]
    x, zs = x[keep], zs[keep]
    if x.size < 5:
        return pd.DataFrame(columns=BAR_COLUMNS)

    crests = find_peaks(zs)[0]
    troughs = find_peaks(-zs)[0]
    rows = []
    for c in crests:
        landward = troughs[troughs < c]
        if landward.size == 0:
            continue
        lt = landward[-1]
        seaward = troughs[troughs > c]
        if seaward.size:
            st, z_st = seaward[0], zs[seaward[0]]
        else:
            st = x.size - 1
            z_st = min(zs[st], zs[lt])
            if z_st >= zs[c]:
                continue
        height = bar_height(x[lt], x[c], x[st], zs[lt], zs[c], z_st)
        rows.append({
            "crest_x": x[c],
            "crest_z": zs[c],
            "height": height,
            "depth": reference_level - zs[c],
            "trough_land_x": x[lt],
            "trough_sea_x": x[st],
            "slope_land": (zs[c] - zs[lt]) / (x[c] - x[lt]),
            "slope_sea": (zs[c] - z_st) / (x[st] - x[c]),
            "zone": "inner" if x[c] <= zone_split else "outer",
        })
    bars = pd.DataFrame(rows, columns=BAR_COLUMNS)
    if keep_all or bars.empty:
        return bars
    limit = np.where(bars["zone"] == "inner", min_height[0], min_height[1])
    keep = (bars["crest_x"] > min_distance) & (bars["height"] > limit)
    return bars[keep].reset_index(drop=True)


def sandbar_table(profiles: pd.DataFrame, **options) -> pd.DataFrame:
    """:func:`find_sandbars` for every survey.

    Returns one row per bar with a ``time`` column first; ``options`` are
    passed to :func:`find_sandbars`.
    """
    table = _with_numeric_columns(profiles)
    x = table.columns.to_numpy(dtype=float)
    parts = []
    for when, row in zip(table.index, table.to_numpy()):
        bars = find_sandbars(x, row, **options)
        if len(bars):
            bars.insert(0, "time", when)
            parts.append(bars)
    if not parts:
        return pd.DataFrame(columns=["time"] + BAR_COLUMNS)
    return pd.concat(parts, ignore_index=True)


def bar_state(bars: pd.DataFrame, times=None) -> pd.DataFrame:
    """Bar configuration of each survey, from :func:`sandbar_table` output.

    For each survey: ``n_inner``, ``n_outer``, ``profile_type`` (1 unbarred,
    2 inner bar only, 3 outer bar only, 4 both; see :data:`PROFILE_TYPES`)
    and the properties of the highest inner and outer bar (``inner_crest_x``,
    ``inner_height``, ``inner_depth``, ``inner_slope_land``,
    ``inner_slope_sea``, and the same with ``outer_``).

    ``times`` lists all surveys so that unbarred ones appear too (pass the
    profile table's index).
    """
    index = pd.DatetimeIndex(times if times is not None else bars["time"].unique())
    out = pd.DataFrame(index=index.unique().sort_values())
    out.index.name = "time"
    for zone in ("inner", "outer"):
        part = bars[bars["zone"] == zone]
        out[f"n_{zone}"] = part.groupby("time").size().reindex(out.index, fill_value=0)
        highest = part.loc[part.groupby("time")["height"].idxmax()].set_index("time") \
            if len(part) else pd.DataFrame(columns=BAR_COLUMNS)
        for column in ("crest_x", "height", "depth", "slope_land", "slope_sea"):
            out[f"{zone}_{column}"] = highest[column].reindex(out.index) if len(part) else np.nan
    has_inner, has_outer = out["n_inner"] > 0, out["n_outer"] > 0
    out.insert(0, "profile_type", 1 + has_inner.astype(int) + 2 * has_outer.astype(int))
    return out
