"""Figures for storms and beach response (``pck.plot``).

Every function draws on ``ax`` when given (for multi-panel figures) and
otherwise creates a new figure. They return the axis. Importing the package
does not change matplotlib settings; call :func:`use_style` for the compact
publication style.
"""

from __future__ import annotations

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap, LogNorm
from matplotlib.offsetbox import AnchoredText
from matplotlib.patches import Patch
import pandas as pd

from .beach import _with_numeric_columns
from .skill import skill_scores
from .storms import StormCriteria

__all__ = [
    "PALETTE",
    "use_style",
    "plot_storm_timeline",
    "plot_storm_counts",
    "plot_profiles",
    "plot_sandbars",
    "plot_beach_response",
    "plot_density_scatter",
    "plot_wave_rose",
]

#: Nine-colour palette: teal, red, blue, orange, yellow, purple, grey, pale cyan, light blue
PALETTE = ["#0091A0", "#E60046", "#00AAE6", "#FA7350", "#FAB423", "#8C5AB4", "#595959",
           "#C5FFFD", "#88D9E6"]
INDIVIDUAL_COLOR = PALETTE[6]
CLUSTER_COLOR = PALETTE[1]
DENSITY_CMAP = ListedColormap(["#C7E5DF", "#D9E2B6", "#E5CA8A", "#DFA55F", "#C63732"],
                              name="pycoastkit_density")


def use_style(font_size: float = 8, dpi: int = 150) -> None:
    """Compact style for journal figures, based on the SciencePlots 'nature' style."""
    plt.rcdefaults()
    try:
        import scienceplots  # noqa: F401  (registers the styles)

        plt.style.use(["science", "no-latex", "nature"])
    except Exception:  # keep working if a matplotlib update breaks SciencePlots
        pass
    grey = PALETTE[6]
    plt.rcParams.update({
        "font.size": font_size, "axes.titlesize": font_size, "axes.labelsize": font_size,
        "xtick.labelsize": font_size, "ytick.labelsize": font_size,
        "legend.fontsize": font_size, "mathtext.default": "regular",
        "axes.labelcolor": grey, "xtick.color": grey, "ytick.color": grey,
        "axes.edgecolor": grey, "axes.grid": True, "grid.color": grey,
        "grid.linewidth": 0.05, "figure.dpi": dpi, "savefig.dpi": dpi,
        "figure.autolayout": True,
    })


def _axis(ax, figsize):
    if ax is None:
        _, ax = plt.subplots(figsize=figsize)
    return ax


def _clean(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(which="minor", bottom=False, left=False)


def plot_storm_timeline(waves, storms: pd.DataFrame, criteria: StormCriteria | None = None,
                        start=None, end=None, hs_column: str = "hs", ax=None,
                        figsize=(6, 2)):
    """Hs time series with storms shaded (grey = individual, red = clustered)
    and the two thresholds as dashed lines."""
    criteria = criteria or StormCriteria()
    hs = (waves if isinstance(waves, pd.Series) else waves[hs_column]).sort_index()
    hs = hs.loc[start:end]
    ax = _axis(ax, figsize)
    ax.plot(hs.index, hs.to_numpy(), lw=0.4, color="k")
    shown = storms[(storms["end_time"] >= hs.index.min()) & (storms["start_time"] <= hs.index.max())]
    for _, storm in shown.iterrows():
        mask = (hs.index >= storm["start_time"]) & (hs.index <= storm["end_time"])
        color = CLUSTER_COLOR if storm.get("kind", "individual") == "clustered" else INDIVIDUAL_COLOR
        ax.fill_between(hs.index, criteria.hs_threshold, hs.to_numpy(),
                        where=mask & (hs.to_numpy() > criteria.hs_threshold),
                        color=color, edgecolor="none", interpolate=True)
    for level in (criteria.hs_threshold, criteria.peak_threshold):
        ax.axhline(level, lw=0.4, color="grey", linestyle="--")
    ax.set_ylabel("H$_s$ [m]")
    ax.legend(handles=[Patch(color=INDIVIDUAL_COLOR, label="Individual storm"),
                       Patch(color=CLUSTER_COLOR, label="Storm cluster")],
              loc="upper right", frameon=False, fontsize="small")
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
    _clean(ax)
    return ax


def plot_storm_counts(storms: pd.DataFrame, by: str = "year", ax=None, figsize=(4, 1.6)):
    """Bar chart of storm counts per ``"year"`` or ``"month"`` (seasonality),
    split into individual storms and storms that belong to clusters."""
    if by not in ("year", "month"):
        raise ValueError("by must be 'year' or 'month'")
    when = pd.to_datetime(storms["start_time"])
    key = when.dt.year if by == "year" else when.dt.month
    kind = storms.get("kind", pd.Series("individual", index=storms.index))
    table = pd.crosstab(key, kind)
    full = range(1, 13) if by == "month" else range(int(key.min()), int(key.max()) + 1)
    table = table.reindex(full, fill_value=0)
    ax = _axis(ax, figsize)
    bottom = np.zeros(len(table))
    for name, color, label in (("individual", INDIVIDUAL_COLOR, "Individual"),
                               ("clustered", CLUSTER_COLOR, "In a cluster")):
        if name in table:
            ax.bar(table.index, table[name], bottom=bottom, color=color, label=label)
            bottom += table[name].to_numpy()
    if by == "month":
        ax.set_xticks(range(1, 13), list("JFMAMJJASOND"))
    ax.set_ylabel("Storms")
    ax.legend(frameon=False, fontsize="small")
    ax.grid(lw=0.1, axis="y")
    _clean(ax)
    return ax


def plot_profiles(profiles: pd.DataFrame, start=None, end=None, water_level=None,
                  shoreline=None, ax=None, figsize=(4.8, 2.0)):
    """Overlay the beach profiles surveyed between ``start`` and ``end``.

    ``water_level`` draws the shoreline-defining level; ``shoreline`` (a
    position in m, or a Series indexed like the profiles) marks the detected
    shoreline. Handy for checking surveys flagged as outliers.
    """
    table = _with_numeric_columns(profiles).loc[start:end]
    ax = _axis(ax, figsize)
    x = table.columns.to_numpy(dtype=float)
    colors = plt.cm.viridis(np.linspace(0, 1, max(len(table), 2)))
    for color, (when, row) in zip(colors, table.iterrows()):
        ax.plot(x, row.to_numpy(), lw=0.6, color=color, label=f"{when:%Y-%m-%d}")
    if water_level is not None:
        ax.axhline(water_level, color="k", lw=0.4, linestyle="--")
    if shoreline is not None:
        positions = shoreline.loc[table.index] if isinstance(shoreline, pd.Series) else [shoreline]
        for pos in np.atleast_1d(positions):
            ax.axvline(pos, color=PALETTE[1], lw=0.4)
    ax.set_xlabel("Cross-shore distance [m]")
    ax.set_ylabel("Elevation [m]")
    if len(table) <= 10:
        ax.legend(frameon=False, fontsize="x-small")
    _clean(ax)
    return ax


def plot_beach_response(response: pd.DataFrame, x: str = "storm_power",
                        y: str = "shoreline_loss", ax=None, figsize=(3, 2.4)):
    """Scatter of storm forcing (``x``) against beach change (``y``), coloured
    by individual (grey) or clustered (red) events, with a zero line."""
    ax = _axis(ax, figsize)
    kind = response.get("kind", pd.Series("individual", index=response.index))
    for name, color, label in (("individual", INDIVIDUAL_COLOR, "Individual"),
                               ("clustered", CLUSTER_COLOR, "Cluster")):
        part = response[kind == name]
        if len(part):
            ax.scatter(part[x], part[y], s=8, color=color, edgecolor="white", linewidth=0.3,
                       label=label)
    ax.axhline(0, color="k", lw=0.4)
    ax.set_xlabel({"storm_power": "Storm power [m² h]"}.get(x, x))
    ax.set_ylabel({"shoreline_loss": "Shoreline retreat [m]",
                   "volume_loss": "Volume loss [m³/m]"}.get(y, y))
    ax.legend(frameon=False, fontsize="small")
    _clean(ax)
    return ax


def plot_density_scatter(observed, predicted, xlabel="Observed", ylabel="Predicted",
                         gridsize=25, ax=None, figsize=(3.2, 2.8)):
    """Observed vs predicted as a hexbin density (log colours) with the 1:1
    line, matching percentiles (white circles) and a skill box."""
    o = np.asarray(observed, dtype=float)
    p = np.asarray(predicted, dtype=float)
    keep = np.isfinite(o) & np.isfinite(p)
    o, p = o[keep], p[keep]
    ax = _axis(ax, figsize)
    hb = ax.hexbin(o, p, gridsize=gridsize, cmap=DENSITY_CMAP, norm=LogNorm(), mincnt=1)
    lims = [min(o.min(), p.min()), max(o.max(), p.max())]
    ax.plot(lims, lims, color=PALETTE[1], lw=0.5)
    levels = [25, 50, 75, 90, 95, 98]
    ax.plot(np.percentile(o, levels), np.percentile(p, levels), "o", mfc="none", mec="white",
            mew=0.8, ms=4, zorder=5)
    s = skill_scores(o, p)
    text = (f"RMSE: {s['rmse']:.2f}\nBias: {s['bias']:.2f}\nR²: {s['r2']:.2f}\n"
            f"rₛ: {s['spearman']:.2f}\nN: {s['n']:,}")
    ax.add_artist(AnchoredText(text, loc="lower right", frameon=False,
                               prop={"size": 6, "color": PALETTE[6]}))
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.figure.colorbar(hb, ax=ax, pad=0.02, label="Count")
    return ax


def plot_wave_rose(directions_deg, n_sectors: int = 16, ax=None, color=PALETTE[0],
                   figsize=(2.2, 2.2)):
    """Frequency rose of wave directions [degrees, coming from, clockwise from north]."""
    if ax is None:
        fig = plt.figure(figsize=figsize)
        ax = fig.add_subplot(projection="polar")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    d = np.asarray(directions_deg, dtype=float)
    d = np.radians(d[np.isfinite(d)] % 360)
    edges = np.linspace(0, 2 * np.pi, n_sectors + 1)
    counts, _ = np.histogram(d, bins=edges)
    freq = counts / counts.sum() if counts.sum() else counts.astype(float)
    ax.bar((edges[:-1] + edges[1:]) / 2, freq, width=2 * np.pi / n_sectors, color=color,
           edgecolor="k", linewidth=0.3)
    ax.set_yticklabels([])
    return ax


def plot_sandbars(x, elevation, bars: pd.DataFrame, reference_level=None, ax=None,
                  figsize=(4.8, 2.0)):
    """One profile with its detected bars: crest (triangle), troughs (dots) and
    the trough-to-trough line used for the bar height.

    ``bars`` is the output of :func:`pycoastkit.find_sandbars` for this profile.
    """
    ax = _axis(ax, figsize)
    x = np.asarray(x, dtype=float)
    z = np.asarray(elevation, dtype=float)
    ax.plot(x, z, color="k", lw=0.8)
    if reference_level is not None:
        ax.axhline(reference_level, color=PALETTE[0], lw=0.5, linestyle="--")
    for _, bar in bars.iterrows():
        color = PALETTE[2] if bar["zone"] == "inner" else PALETTE[5]
        z_land = np.interp(bar["trough_land_x"], x, z)
        z_sea = bar["crest_z"] - bar["slope_sea"] * (bar["trough_sea_x"] - bar["crest_x"])
        ax.plot([bar["trough_land_x"], bar["trough_sea_x"]], [z_land, z_sea], color=color,
                lw=0.6, linestyle=":")
        ax.plot(bar["crest_x"], bar["crest_z"], "^", color=color, ms=5,
                label=f"{bar['zone']} bar, h = {bar['height']:.2f} m")
        ax.plot([bar["trough_land_x"], bar["trough_sea_x"]], [z_land, z_sea], "o", color=color,
                ms=3)
    ax.set_xlabel("Cross-shore distance [m]")
    ax.set_ylabel("Elevation [m]")
    if len(bars):
        ax.legend(frameon=False, fontsize="x-small")
    _clean(ax)
    return ax
