# pycoastkit

**A toolkit for sandy coasts.** `pycoastkit` finds storms in wave records,
describes the beach from cross-shore profile surveys (shoreline position,
sand volume, slopes and sandbars), measures how much each storm eroded the
beach and how much came back afterwards, and scores beach vulnerability. It
also downloads and quality-controls the long Hasaki (Japan) wave and
beach-profile records.

```bash
pip install pycoastkit
```

<div class="pck-cards">
  <div><div class="tag">FORCING</div><strong>Storms</strong><span>Wave record to storms and independent storm events</span></div>
  <div><div class="tag">STATE</div><strong>Beach</strong><span>Profiles to shoreline, volume, slope and sandbars</span></div>
  <div><div class="tag">RESPONSE</div><strong>Impacts</strong><span>Erosion per event, then recovery</span></div>
  <div><div class="tag">RISK</div><strong>Vulnerability</strong><span>Vulnerability and susceptibility indices, return periods</span></div>
</div>

## What you can do with it

| Task | Functions |
|---|---|
| Find storms and storm clusters in an Hs record | [`find_storms`](api/storms.md), [`storm_clusters`](api/storms.md) |
| Shoreline position at any water level | [`shoreline_positions`](api/shoreline.md) |
| Sand volume in beach, inner and outer surf zones | [`beach_volume`](api/beach.md), [`shoreline_relative_profiles`](api/beach.md) |
| Detect sandbars and classify the bar configuration | [`find_sandbars`](api/sandbars.md), [`bar_state`](api/sandbars.md) |
| Shoreline retreat and volume loss caused by each storm | [`storm_beach_response`](api/impacts.md) |
| Beach recovery after storms | [`storm_recovery`](api/recovery.md) |
| Beach vulnerability and susceptibility indices | [`add_vulnerability_index`](api/vulnerability.md), [`susceptibility_index`](api/vulnerability.md) |
| Hasaki wave and profile data | [`pck.hasaki`](hasaki.md) |

## A first example

```python
import pycoastkit as pck

storms = pck.find_storms(waves)              # waves: time-indexed table with an "hs" column
events = pck.storm_clusters(storms)          # one row per independent event

beach = pck.shoreline_positions(profiles, water_level=1.25, smooth_sigma=2).to_frame()
beach["volume"] = pck.beach_volume(pck.smooth_profiles(profiles), x_min=-40, x_max=60)

impact = pck.storm_beach_response(events, beach)
print(impact[["start_time", "kind", "storm_power", "shoreline_loss", "volume_loss"]])
```

Continue with [Getting started](getting-started.md) for the full workflow, or
read the [User guide](guide/index.md) for how each method works.

## Author

Developed by [Salika Thilakarathne](https://www.hereon.de/institutes/coastal_systems_analysis_modeling/coastal_climate_regional_sea_level_changes/team/114121/index.php.en),
Helmholtz-Zentrum Hereon. Released under the MIT licence.
