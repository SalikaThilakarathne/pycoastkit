# Impacts and recovery

## Beach change across a storm

`storm_beach_response(storms, beach, days_before=1, days_after=1, max_search_days=7)`
measures the change in each beach indicator across each storm or storm
cluster.

- The **pre-storm survey** is the last valid survey on or before the day
  `days_before` days before the storm started.
- The **post-storm survey** is the first valid survey on or after the day
  `days_after` days after the storm ended.
- If no valid survey exists within `max_search_days`, the result is NaN
  rather than a comparison with a survey from weeks away.

Working in whole days keeps surveys made during the storm out of the
comparison. `beach` can hold any number of indicators (for example the
output of `pck.hasaki.hasaki_beach_state`, with `shoreline` and `volume`).
Each column `c` produces:

| Column | Meaning |
|---|---|
| `c_pre_time`, `c_pre` | Date and value of the pre-storm survey |
| `c_post_time`, `c_post` | Date and value of the post-storm survey |
| `c_loss` | `c_pre - c_post`; positive means erosion (shoreline retreat or volume loss), negative means accretion |

`survey_before(series, when, max_days)` and `survey_after(...)` are the
helpers it uses and can be called directly.

## Recovery after a storm

After a storm, lower waves move sand from the bar zone back to the beach. How
fast this happens decides whether the next storm meets a recovered or a
still-eroded beach.

`storm_recovery(response, beach, n_days=10, max_search_days=3, min_loss=None)`
starts from the post-storm survey and takes the survey `n_days` later (the
last valid survey within `max_search_days` before that day). For each
indicator `c` it adds:

| Column | Meaning |
|---|---|
| `c_recovery_time` | Date of the survey used |
| `c_recovery` | `c_later - c_post`; positive means the beach rebuilt |
| `c_recovery_ratio` | `c_recovery / c_loss`: 1 = fully recovered, above 1 = more than recovered, below 0 = erosion continued |
| `undisturbed` | True when the next storm came after the recovery window (needs `gap_after_h` from `find_storms`) |

!!! tip "Use a minimum erosion"
    The recovery ratio becomes unstable when a storm eroded very little. Set
    `min_loss`, for example to the mean erosion (about 5 m of shoreline at
    Hasaki), keep only `undisturbed` events, and remove extreme ratios with
    `iqr_outliers(values, k=1.5)` before computing statistics.

## Conditions during recovery

`post_storm_conditions(storms, waves, statistics, n_days=10)` summarises any
wave or water-level variable in the window after each storm:

```python
recovery = pck.post_storm_conditions(storms, waves, {"hs": ["mean", "max"], "ts": "mean"})
# adds post_mean_hs, post_max_hs and post_mean_ts
```
