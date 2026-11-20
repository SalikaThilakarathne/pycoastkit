# User guide

The guide explains how each method works, which choices it makes and what
its output means. For the full list of parameters, follow the links to the
[API reference](../api/index.md).

The analysis follows the chain from forcing to response:

1. **[Storms](storms.md)**: find storm events in a wave record and group
   dependent storms into clusters.
2. **[Beach profiles](beach.md)**: smooth surveys, express them relative to
   the shoreline, and compute sand volumes and slopes.
3. **[Shoreline](shoreline.md)**: shoreline position at any water level and
   foreshore slope.
4. **[Sandbars](sandbars.md)**: detect bars and classify the bar
   configuration of each survey.
5. **[Impacts and recovery](impacts.md)**: beach change across each storm
   and the recovery that follows.
6. **[Vulnerability](vulnerability.md)**: erosion classes, the beach
   vulnerability index, a susceptibility index and return periods.
7. **[Waves](waves.md)**: wave energy flux, storm surge, and sea-state
   statistics from surface-elevation records.
8. **[Plots](plots.md)**: figures for each step.

## Conventions

| Quantity | Convention |
|---|---|
| Cross-shore position `x` | metres, increasing seaward |
| Elevation `z` | metres, in the survey datum (at Hasaki: Hasaki Port datum) |
| Shoreline change, volume change | `loss = before - after`; positive means erosion |
| Recovery | `after - post-storm`; positive means the beach rebuilt |
| Wave height `hs` | significant wave height in metres |
| Time | pandas `DatetimeIndex` |
