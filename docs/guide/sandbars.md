# Sandbars

Sandbars are shore-parallel ridges of sand in the surf zone. Large waves
break over them, so a beach with a well-developed bar usually loses less
sand in a storm. `pck.sandbars` finds the bars on each survey and describes
them. Work on [shoreline-relative profiles](beach.md#shoreline-relative-profiles)
so that bar positions are distances from the shoreline.

<figure class="pck-figure" markdown="0">
<svg viewBox="0 0 720 220" role="img" aria-label="Barred profile with crest, troughs, trough-to-trough line, bar height and depth below the reference level">
  <rect class="fill-sea" x="60" y="40" width="660" height="160"/>
  <line class="tealline" x1="20" y1="40" x2="700" y2="40"/>
  <text class="teal" x="545" y="33">reference level (MHWS)</text>
  <path class="line" d="M20,20 C50,30 70,45 100,70 C160,115 200,140 240,150 C270,156 300,120 330,110 C360,104 390,140 420,165 C460,185 490,160 540,150 C570,145 600,170 640,186 L700,192"/>
  <line class="reddash" x1="240" y1="150" x2="420" y2="165"/>
  <circle class="dot" cx="240" cy="150" r="4"/>
  <circle class="dot" cx="420" cy="165" r="4"/>
  <circle class="dot-red" cx="330" cy="110" r="5"/>
  <line class="axis" x1="330" y1="110" x2="330" y2="157"/>
  <text class="red" x="338" y="140">height</text>
  <line class="axis" x1="300" y1="40" x2="300" y2="110"/>
  <text class="strong" x="250" y="80">depth</text>
  <text class="strong" x="305" y="100">crest</text>
  <text x="190" y="172">landward trough</text>
  <text x="396" y="186">seaward trough</text>
  <text x="24" y="212">shoreline (x' = 0)</text>
  <text x="664" y="212">sea</text>
</svg>
<figcaption>Bar height is measured from the crest down to the straight line joining
the two troughs (dashed), so a bar on a sloping seabed is neither over- nor
under-estimated. Depth is measured from the reference level down to the crest.</figcaption>
</figure>

## Detecting bars

`find_sandbars(x, elevation, ...)` works on one profile:

1. The profile is smoothed (Gaussian, `smooth_sigma` grid points) and then
   cut to `x_range` (default: from the shoreline seaward).
2. Crests are local maxima and troughs local minima. Each crest is paired
   with the nearest trough on each side. If the profile keeps falling seaward
   of the last crest, its last point serves as the seaward trough. A crest
   with no landward trough belongs to the beach face and is skipped.
3. A bar is kept if its crest is more than `min_distance` from the shoreline
   and its height exceeds `min_height[0]` in the inner zone (crest within
   `zone_split`) or `min_height[1]` in the outer zone.

The bar height is

$$
h = z_c - \left[ z_{s} + (z_{l} - z_{s}) \frac{x_c - x_{s}}{x_{l} - x_{s}} \right]
$$

with crest $(x_c, z_c)$, landward trough $(x_l, z_l)$ and seaward trough
$(x_s, z_s)$.

The defaults are the values used for Hasaki: bars more than 50 m from the
shoreline, an inner zone up to 170 m, minimum heights of 0.24 m (inner) and
0.5 m (outer), and depth below MHWS 1.25 m. For another beach, run with
`keep_all=True` first to see every crest, then choose thresholds from the
height distribution.

| Column | Meaning |
|---|---|
| `crest_x`, `crest_z` | Crest position [m] and elevation [m] |
| `height` | Crest above the trough-to-trough line [m] |
| `depth` | `reference_level - crest_z`, water depth over the crest [m] |
| `trough_land_x`, `trough_sea_x` | Positions of the two troughs [m] |
| `slope_land`, `slope_sea` | Crest-to-trough gradients on each side (positive) |
| `zone` | `"inner"` or `"outer"` |

## Bar configuration of each survey

```python
relative = pck.shoreline_relative_profiles(profiles, shoreline)
bars = pck.sandbar_table(relative)                 # one row per bar, with a "time" column
state = pck.bar_state(bars, times=profiles.index)  # one row per survey
```

`bar_state` gives the number of inner and outer bars, the properties of the
highest bar in each zone (`inner_crest_x`, `inner_height`, `inner_depth`,
`inner_slope_land`, `inner_slope_sea`, and the same for `outer_`), and the
**profile type**:

| `profile_type` | Bar configuration |
|---|---|
| 1 | Unbarred |
| 2 | Inner bar only |
| 3 | Outer bar only |
| 4 | Inner and outer bars |

Pass `times=profiles.index` so that unbarred surveys are included.
`pck.plot.plot_sandbars` draws one profile with its crests, troughs and
trough lines, which is the quickest way to check the detection.
