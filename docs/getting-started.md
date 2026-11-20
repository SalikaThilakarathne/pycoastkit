# Getting started

## Installation

```bash
pip install pycoastkit
```

One install includes everything: the analysis functions, figures, the
Hasaki data tools and the `pycoastkit` command. It needs Python 3.10 or
newer and installs numpy, scipy, pandas, matplotlib, pyarrow (parquet files)
and SciencePlots (journal figure style).

After `import pycoastkit as pck`, every module is available as
`pck.<module>` and the main functions directly as `pck.<function>`:

| Module | Topic |
|---|---|
| `pck.storms` | Storm detection, clusters, storm power and energy |
| `pck.beach` | Profile smoothing, shoreline-relative profiles, volumes, cut and fill, slopes |
| `pck.shoreline` | Shoreline at any water level, foreshore slope, outlier check |
| `pck.sandbars` | Sandbar detection and profile type |
| `pck.impacts` | Beach change across each storm |
| `pck.recovery` | Beach recovery after storms |
| `pck.vulnerability` | Vulnerability and susceptibility indices, return periods |
| `pck.waves` | Energy flux, surge, sea-state and rogue-wave statistics |
| `pck.skill` | Model skill scores |
| `pck.plot` | Figures |
| `pck.hasaki` | Hasaki wave and beach-profile data |

## Input data

`pycoastkit` works with two kinds of tables.

**Wave records** are time-indexed tables with significant wave height in a
column named `hs` (metres). Other columns, such as period `ts` or direction,
are optional.

**Profile tables** hold repeated cross-shore beach surveys: one row per
survey (time index) and one column per cross-shore position in metres,
increasing seaward. Values are bed elevations in metres. Column labels such
as `"-40m"` are converted automatically.

## The complete workflow

The example below runs the full analysis for Hasaki, from raw downloads to
one row per storm event with its erosion, recovery and vulnerability.

```python
import pycoastkit as pck

# waves: download once and keep the files
files = pck.hasaki.download_nowphas(range(1987, 2023), "nowphas_kashima")
waves, qc_report = pck.hasaki.qc_nowphas(pck.hasaki.read_nowphas(files))

# 1. storms and independent events
criteria = pck.StormCriteria(hs_threshold=1.5, peak_threshold=2.5,
                             min_duration_h=6, min_separation_h=48)
storms = pck.find_storms(waves, criteria)
events = pck.storm_clusters(storms)

# 2. beach state from the HORS profiles
profiles = pck.hasaki.read_hors_profiles("hors_profiles.csv")   # elevations in cm
beach = pck.hasaki.hasaki_beach_state(profiles)                  # shoreline [m], volume [m3/m]

# 3. sandbars, measured from the shoreline
relative = pck.shoreline_relative_profiles(profiles, beach["shoreline"])
bars = pck.sandbar_table(relative)
state = pck.bar_state(bars, times=profiles.index)                # profile type 1-4

# 4. erosion, recovery and vulnerability of every event
impact = pck.storm_beach_response(events, beach)
impact = pck.storm_recovery(impact, beach, n_days=10)
impact = pck.add_vulnerability_index(impact)

# 5. figures
pck.plot.use_style()
pck.plot.plot_storm_timeline(waves, storms, criteria, start="2006-10-01", end="2006-11-15")
pck.plot.plot_beach_response(impact)
```

Any other site works the same way: give `find_storms` a wave record and
give `storm_beach_response` a time-indexed table of beach indicators.
