# Shoreline

## Shoreline position

`shoreline_positions(profiles, water_level, crossing="seaward", smooth_sigma=None)`
finds where each profile crosses `water_level`. The profile is scanned for
**down-crossings**, where the bed goes from above to below the level, and the
crossing is linearly interpolated between the two survey points around it,
so the result is not limited to the survey grid. A profile that never
crosses the level gives NaN.

| Parameter | Meaning |
|---|---|
| `water_level` | Shoreline-defining level in the survey datum. At Hasaki: mean high water springs (MHWS) 1.25 m, mean sea level 0.65 m, low water −0.2 m |
| `crossing` | `"seaward"` (default, as in the Hasaki studies) takes the outermost down-crossing; `"landward"` takes the first, at the beach face. They differ only when an emerged bar or a runnel crosses the level a second time |
| `smooth_sigma` | Smooth the profiles first (grid points); `2` suits daily surveys |

For a single profile, use `shoreline_position(x, elevation, water_level)`.

## Foreshore slope

`foreshore_slope(profiles, upper_level, lower_level)` is the mean slope
between two contours:

$$
\tan\beta = \frac{z_{\mathrm{upper}} - z_{\mathrm{lower}}}{x_{\mathrm{lower}} - x_{\mathrm{upper}}}
$$

For Hasaki use `upper_level=1.25` (MHWS) and `lower_level=-0.2` (low water).
The foreshore slope controls how waves run up the beach: steep foreshores
reflect more wave energy, gentle ones dissipate it.

## Checking shoreline series

`flag_shoreline_outliers(shoreline, window=5, z_threshold=1.73)` finds
surveys that jump away from their neighbours. A centred rolling mean and
standard deviation over `window` surveys give a local z-score, and surveys
with $|z|$ above `z_threshold` are flagged.

!!! note "Check before removing"
    Real storm erosion is also abrupt. Look at each flagged survey with
    `pck.plot.plot_profiles` before removing it. Shorelines from smoothed
    profiles usually need no correction.
