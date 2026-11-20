# Storms

## How a storm is defined

A storm is defined with two wave-height thresholds, a minimum duration and
an independence gap. The lower threshold sets when a storm starts and ends.
The upper threshold makes sure the storm was strong enough to affect the
beach. Two storms that follow each other closely are not independent: the
beach has no time to recover in between, so they form a **storm cluster**.

<figure class="pck-figure" markdown="0">
<svg viewBox="0 0 720 270" role="img" aria-label="Significant wave height record with two thresholds, a storm cluster and an individual storm">
  <line class="axis" x1="60" y1="220" x2="700" y2="220"/>
  <line class="axis" x1="60" y1="20" x2="60" y2="220"/>
  <text x="22" y="24">Hs</text>
  <text x="660" y="240">time</text>
  <path class="fill-red" d="M128,150 L140,120 L160,70 L180,95 L200,120 L214,150 Z"/>
  <path class="fill-red" d="M262,150 L280,110 L300,55 L320,80 L340,125 L350,150 Z"/>
  <path class="fill-grey" d="M520,150 L540,105 L560,62 L580,85 L600,125 L612,150 Z"/>
  <polyline class="line" points="60,190 90,180 110,170 128,150 140,120 160,70 180,95 200,120 214,150 230,170 246,165 262,150 280,110 300,55 320,80 340,125 350,150 370,180 400,195 430,175 450,160 465,170 490,185 505,170 520,150 540,105 560,62 580,85 600,125 612,150 630,175 660,190 700,185"/>
  <line class="dash" x1="60" y1="150" x2="700" y2="150"/>
  <line class="dash" x1="60" y1="100" x2="700" y2="100"/>
  <text x="64" y="145">hs_threshold (1.5 m)</text>
  <text x="64" y="95">peak_threshold (2.5 m)</text>
  <text x="420" y="144">too weak</text>
  <path class="axis" d="M520,232 L520,238 L612,238 L612,232"/>
  <text x="520" y="256">duration &#8805; min_duration_h</text>
  <path class="axis" d="M214,232 L214,238 L262,238 L262,232"/>
  <text x="160" y="256">gap &#8804; min_separation_h</text>
  <path class="axis" d="M350,205 L350,211 L520,211 L520,205"/>
  <text x="372" y="200">gap &gt; min_separation_h</text>
  <text class="red" x="140" y="40">storm cluster (2 storms)</text>
  <text class="strong" x="505" y="40">individual storm</text>
</svg>
<figcaption>A storm (shaded) keeps Hs above <code>hs_threshold</code> for at least
<code>min_duration_h</code> and peaks above <code>peak_threshold</code>. The first two
storms are separated by a short calm and form one cluster. The defaults are
the storm definition used for the Hasaki coast.</figcaption>
</figure>

```python
criteria = pck.StormCriteria(hs_threshold=1.5, peak_threshold=2.5,
                             min_duration_h=6, min_separation_h=48)
```

Choose the thresholds for your coast. A common approach is a high percentile
of Hs (for example the 95th) for `hs_threshold`, and a value linked to
observed beach damage for `peak_threshold`.

## Finding storms

[`find_storms`](../api/storms.md) scans the record:

1. Every run of consecutive samples with Hs above `hs_threshold` is a
   candidate. A missing value, or a gap in the record longer than 1.5
   sampling intervals, ends the run, so a storm never bridges missing data.
2. The duration is the number of samples in the run times the sampling
   interval, that is, the time spent above the threshold.
3. The candidate is kept if it is long enough and its peak reaches
   `peak_threshold`.
4. Neighbouring storms with a calm gap of `min_separation_h` or less receive
   the same `cluster_id`.

The result has one row per storm:

| Column | Meaning |
|---|---|
| `storm_id` | 1, 2, 3 ... in time order |
| `cluster_id` | Independent event the storm belongs to |
| `kind` | `"individual"`, or `"clustered"` when its cluster has more than one storm |
| `n_in_cluster` | Number of storms in the cluster |
| `start_time`, `end_time` | First and last sample above `hs_threshold` |
| `duration_h` | Time above the threshold [h] |
| `peak_hs`, `peak_time` | Highest Hs [m] and when it occurred |
| `mean_hs` | Mean Hs during the storm [m] |
| `storm_power` | $H_{s,\max}^2 \cdot D$ [m² h], a storm intensity measure (Dolan and Davis, 1992) |
| `gap_before_h`, `gap_after_h` | Calm time to the previous and next storm [h] |

## Storm clusters

[`storm_clusters`](../api/storms.md) combines the storms of each cluster into
one event. Individual storms come through as clusters of one, so the result
is a single table of independent events. Use it whenever storms are related
to beach change, because the beach responds to the cluster as a whole.

| Column | How it is combined |
|---|---|
| `n_storms` | Storms in the cluster |
| `start_time`, `end_time` | Start of the first storm, end of the last |
| `span_h` | Elapsed time from first start to last end, calm spells included |
| `duration_h` | Sum of the storm durations (stormy time only) |
| `peak_hs`, `peak_time` | Highest peak in the cluster |
| `mean_hs` | Duration-weighted mean |
| `storm_power` | Sum over the storms |

## Wave statistics and energy per storm

```python
storms = pck.add_storm_wave_statistics(
    storms, waves, {"ts": ["mean", "max"], "hmax": "max", "direction": "circmean"})
storms = pck.add_storm_energy(storms, waves, hs_column="hs", period_column="ts")
```

`add_storm_wave_statistics` summarises any wave variable over each storm.
Use `"circmean"` for directions, so that 350° and 10° average to 0° rather
than 180°.

`add_storm_energy` integrates the [wave energy flux](waves.md#wave-energy-flux)
over each storm using the actual time steps, so hourly and 2-hourly records
give comparable totals. It adds `energy_mj_per_m` [MJ/m] and
`max_energy_flux_kw_per_m` [kW/m].

## Seasonality and trends

`storms_per_month(storms)` counts storms by calendar month and
`storms_per_year(storms)` by year, including years without storms.
