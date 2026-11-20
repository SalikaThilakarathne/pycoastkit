# Changelog

## 0.1.0 - 2026-11-20

First release of `pycoastkit` (developed from the earlier `wave_storms` draft).

* **storms**: `StormCriteria`, `find_storms` (individual vs clustered storms),
  `storm_clusters`, `storm_power`, `add_storm_wave_statistics`,
  `add_storm_energy`, seasonality counts.
* **beach**: NaN-safe profile smoothing, shoreline-relative profiles
  (interpolated, not snapped to the grid), zone volumes (Simpson's rule),
  cut-and-fill, slopes between two positions.
* **shoreline**: shoreline at any water level with landward or seaward
  crossing (default: seaward, as in the Hasaki studies), foreshore slope
  between two levels, outlier flags.
* **sandbars**: bar detection (crest, height above the trough line, depth,
  landward/seaward slopes, inner/outer zone), per-survey bar state and
  profile type (unbarred, inner, outer, both).
* **impacts**: shoreline and volume change across each storm event.
* **recovery**: recovery of each indicator N days after the storm, recovery
  ratio, post-storm wave statistics, IQR outlier filter.
* **vulnerability**: erosion classes, beach vulnerability index (BVI),
  weighted susceptibility index, return periods of annual maxima.
* **waves**: spectral sea-state parameters, zero-crossing statistics with
  rogue-wave flags, wave energy flux (linear theory), storm surge.
* **skill**, **plot**, the `pycoastkit` command, and **hasaki** data tools
  (NOWPHAS download, reader and QC; HORS profile reader).
