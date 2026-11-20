# Beach profiles

Beach state is measured with repeated cross-shore profile surveys. The
functions take a **profile table**: one row per survey and one column per
cross-shore position in metres, increasing seaward.

<figure class="pck-figure" markdown="0">
<svg viewBox="0 0 720 230" role="img" aria-label="Beach profile with water level, shoreline crossing before and after a storm, and the volume zone">
  <rect class="fill-sea" x="300" y="110" width="400" height="100"/>
  <path class="fill-sand" d="M20,60 C90,58 150,62 200,78 C260,98 300,112 360,140 C430,170 520,168 600,180 L700,186 L700,210 L20,210 Z"/>
  <path class="line" d="M20,60 C90,58 150,62 200,78 C260,98 300,112 360,140 C430,170 520,168 600,180 L700,186"/>
  <path class="reddash" d="M20,60 C90,58 140,64 180,84 C230,108 270,128 330,150 C420,172 520,170 600,181 L700,186"/>
  <line class="tealline" x1="20" y1="110" x2="700" y2="110"/>
  <text class="teal" x="600" y="104">water level</text>
  <circle class="dot" cx="298" cy="110" r="4.5"/>
  <circle class="dot-red" cx="244" cy="110" r="4.5"/>
  <text class="strong" x="306" y="98">shoreline, pre-storm</text>
  <text class="red" x="120" y="134">post-storm</text>
  <line class="dash" x1="120" y1="40" x2="120" y2="210"/>
  <line class="dash" x1="470" y1="40" x2="470" y2="210"/>
  <text x="124" y="36">x_min</text>
  <text x="474" y="36">x_max</text>
  <text x="230" y="200">volume: sand above the lowest observed bed, x_min to x_max</text>
  <text x="24" y="226">land</text>
  <text x="666" y="226">sea</text>
</svg>
<figcaption>The shoreline is where the profile crosses the water level. When a
storm erodes the beach face (dashed), the crossing moves landward and the sand
volume in the zone decreases.</figcaption>
</figure>

## Smoothing

`smooth_profiles(profiles, sigma=2.0)` applies a Gaussian filter along each
profile. `sigma` is in grid points, so `sigma=2` on a 5 m grid smooths over
about 10 m. Small survey errors can create false shoreline crossings and
false sandbar crests; smoothing removes them. Missing points are handled by
normalised convolution: a gap does not spread to its neighbours and stays
missing.

## Shoreline-relative profiles

`shoreline_relative_profiles(profiles, shoreline)` expresses every survey in
coordinates measured from its own shoreline: $x' = x - x_{sl}$, so $x' = 0$
is the shoreline and positive $x'$ is seaward. Elevations are linearly
interpolated onto a fixed grid (default −80 m to 340 m every 5 m), so the
shoreline is not rounded to the survey grid. Sandbar positions and zone
volumes are usually measured in these coordinates because the whole beach
moves with the shoreline.

## Beach volume

`beach_volume(profiles, x_min, x_max, base="min")` gives the sand volume per
metre of coast [m³/m]:

$$
V = \int_{x_{\min}}^{x_{\max}} \left( z(x) - z_{\mathrm{base}}(x) \right) \, dx
$$

integrated with Simpson's rule. With `base="min"` the reference at each
position is the lowest elevation in the whole record, so the result is the
sand stored above the most eroded state observed. A number gives a fixed
reference level instead.

Common zones at Hasaki:

| Zone | Coordinates | Range |
|---|---|---|
| Beach | absolute | −40 m to +60 m |
| Inner surf zone | relative to the shoreline | 20 m to 170 m |
| Outer surf zone | relative to the shoreline | 170 m to 340 m |

A survey with a missing point inside the zone returns NaN, so a partial
survey never appears as erosion.

## Cut and fill

`cut_and_fill(before, after, x_min, x_max)` separates the change between two
surveys into **cut** (sand removed where the bed went down) and **fill**
(sand added where it went up), both positive in m³/m, and the net loss
`cut - fill`. A storm often cuts the beach face and fills the bar zone; the
net change hides this, cut and fill show it.

## Slopes

`profile_slope(profiles, x1, x2)` gives the mean bed slope
$(z(x_1) - z(x_2)) / (x_2 - x_1)$, positive when the bed falls seaward.
Positions are interpolated, so they need not be grid points. On
shoreline-relative profiles, `profile_slope(relative, 0, 150)` is the
nearshore slope. For the foreshore slope between two water levels, see
[Shoreline](shoreline.md#foreshore-slope).
