# pycoastkit

[![Tests](https://github.com/SalikaThilakarathne/pycoastkit/actions/workflows/tests.yml/badge.svg)](https://github.com/SalikaThilakarathne/pycoastkit/actions/workflows/tests.yml)
[![Documentation](https://github.com/SalikaThilakarathne/pycoastkit/actions/workflows/docs.yml/badge.svg)](https://salikathilakarathne.github.io/pycoastkit/)
[![PyPI](https://img.shields.io/pypi/v/pycoastkit.svg)](https://pypi.org/project/pycoastkit/)
[![Python](https://img.shields.io/pypi/pyversions/pycoastkit.svg)](https://pypi.org/project/pycoastkit/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Documentation: <https://salikathilakarathne.github.io/pycoastkit/>**

**A toolkit for sandy coasts.** `pycoastkit` finds storms in wave records,
describes the beach from cross-shore profile surveys (shoreline, sand volume,
slopes, sandbars), measures how much each storm eroded the beach and how much
came back afterwards, and scores beach vulnerability. It also downloads and
quality-controls the long Hasaki (Japan) wave and beach-profile records.

```
waves (Hs) ─► storms ─► clusters ─────────────────┐
                                                   ├─► impacts (erosion) ─► recovery
profiles ─► shoreline · volume · slope · sandbars ─┘          │
                                                              └─► vulnerability index
```

## Install

```bash
pip install pycoastkit
```

One package, everything included: analysis, plots, Hasaki data tools and the
`pycoastkit` command. Python 3.10 or newer.

## Quick start

```python
import pycoastkit as pck

# storms: Hs > 1.5 m for >= 6 h, peak >= 2.5 m; <= 48 h apart = same cluster
storms = pck.find_storms(waves, pck.StormCriteria(1.5, 2.5, min_duration_h=6, min_separation_h=48))
events = pck.storm_clusters(storms)

# beach state from profiles (rows = surveys, columns = cross-shore positions in m)
smooth = pck.smooth_profiles(profiles, sigma=2)
beach = pck.shoreline_positions(smooth, water_level=1.25).to_frame()
beach["volume"] = pck.beach_volume(smooth, x_min=-40, x_max=60)

# sandbars, measured from the shoreline
relative = pck.shoreline_relative_profiles(profiles, beach["shoreline"])
bars = pck.sandbar_table(relative)                 # one row per bar
state = pck.bar_state(bars, times=profiles.index)  # profile type 1-4 per survey

# erosion, recovery and vulnerability per storm event
impact = pck.storm_beach_response(events, beach)
impact = pck.storm_recovery(impact, beach, n_days=10)
impact = pck.add_vulnerability_index(impact)

# figures
pck.plot.use_style()
pck.plot.plot_beach_response(impact)
```

### Hasaki data in three commands

```bash
pycoastkit hasaki download 1987-2022 -d nowphas_kashima   # NOWPHAS Kashima waves
pycoastkit hasaki qc nowphas_kashima -o hasaki_waves.csv   # clean + QC report
pycoastkit storms hasaki_waves.csv --clusters -o hasaki_storms.csv
```

The HORS beach profiles are distributed by PARI on request; read them with
`pck.hasaki.read_hors_profiles`.

## What is inside

One package, one module per topic. All are available after `import pycoastkit as pck`.

```
pycoastkit/
├── storms.py         find_storms, storm_clusters, storm_power, add_storm_energy, ...
├── beach.py          smooth_profiles, shoreline_relative_profiles, beach_volume, cut_and_fill, profile_slope
├── shoreline.py      shoreline_position(s), foreshore_slope, flag_shoreline_outliers
├── sandbars.py       find_sandbars, sandbar_table, bar_state, bar_height
├── impacts.py        storm_beach_response, survey_before, survey_after
├── recovery.py       storm_recovery, post_storm_conditions, iqr_outliers
├── vulnerability.py  erosion_class, beach_vulnerability_index, susceptibility_index, return_periods
├── waves.py          spectral_parameters, individual_wave_statistics, wave_energy_flux, storm_surge
├── skill.py          skill_scores, skill_table, skill_by_quantile
├── plot.py           storm timeline, storm counts, profiles, sandbars, beach response, ...
├── hasaki.py         download_nowphas, read_nowphas, qc_nowphas, read_hors_profiles, hasaki_beach_state
└── cli.py            the `pycoastkit` command
```

New features are added as new modules in the same package, so existing code keeps working.

The [documentation](https://salikathilakarathne.github.io/pycoastkit/)
explains every method, parameter and output column, with a user guide, an
API reference and a glossary of coastal terms.

## Data sources and citation

* Waves: NOWPHAS (Nationwide Ocean Wave information network for Ports and
  HArbourS), observed by the MLIT Ports and Harbours Bureau and processed by
  PARI, https://nowphas.mlit.go.jp/. Free to reuse with attribution; please
  download once and keep the files rather than re-fetching.
* Beach profiles: Hasaki Oceanographical Research Station, PARI. Banno, M.,
  Nakamura, S., Kosako, T., Nakagawa, Y., Yanagishima, S., Kuriyama, Y. (2020).
  Long-term observations of beach variability at Hasaki, Japan. *J. Mar. Sci.
  Eng.* 8, 871. https://doi.org/10.3390/jmse8110871
* Storm power: Dolan, R., Davis, R. E. (1992). An intensity scale for Atlantic
  coast northeast storms. *J. Coastal Res.* 8(4), 840-853.
* Spectral parameters follow Häfner, Gemmrich & Jochum (2021), *Real-world
  rogue wave probabilities*, Sci. Rep. 11, 10084.
* Coastal background: Roelvink, D. and Reniers, A. (2012). *A Guide to
  Modeling Coastal Morphology*. Advances in Coastal and Ocean Engineering,
  Vol. 12. World Scientific. ISBN 978-981-4304-25-2.

## Author and licence

Copyright © 2026 Salika Thilakarathne, Helmholtz-Zentrum Hereon.
Released under the [MIT licence](LICENSE).
