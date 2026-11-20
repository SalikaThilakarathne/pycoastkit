# Hasaki data

Hasaki, on the Pacific coast of Ibaraki Prefecture, Japan, has one of the
longest and densest beach records in the world. A research pier has been
surveyed almost daily since 1986, and an offshore wave station has operated
since the 1970s. `pck.hasaki` turns both records into analysis-ready tables.

## Offshore waves: NOWPHAS Kashima

NOWPHAS (Nationwide Ocean Wave information network for Ports and HArbourS) is
the national wave network operated by MLIT and PARI. Station **Kashima (code
207)** provides 2-hourly wave statistics for 1972–1982, 1984–2008 and
2010–2024, and 20-minute statistics from 2005.

### Download

```python
files = pck.hasaki.download_nowphas(range(1987, 2023), "nowphas_kashima")
```

One file is downloaded per year, using the same request as the NOWPHAS
download form. Years already in the folder are skipped, so the call can be
repeated safely, and years without data (for Kashima, 1983 and 2009) are
skipped with a message.

!!! note "Responsible use"
    NOWPHAS asks users not to collect data automatically on a schedule.
    Download the years you need once and keep the files. If the website
    changes, download the yearly zip files by hand from
    [nowphas.mlit.go.jp/pastdata](https://nowphas.mlit.go.jp/pastdata/) and
    pass them to `read_nowphas`.

### Reading

`read_nowphas(sources)` reads the text files, the downloaded zip files, or a
whole folder (Shift-JIS, fixed width). Raw codes are kept so nothing is
hidden before quality control.

| Column | Meaning | Unit |
|---|---|---|
| `flag` | 0 normal, 4 filled from pressure, 7 filled from analogue chart, 66 calm, 77 not a high wave, 9999 missing | – |
| `n_waves` | Waves in the 20-minute record | – |
| `h_mean`, `t_mean` | Mean wave height and period | m, s |
| `hs`, `ts` | Significant wave ($H_{1/3}$, $T_{1/3}$) | m, s |
| `h_1_10`, `t_1_10` | Highest one-tenth waves | m, s |
| `hmax`, `tmax` | Highest wave | m, s |
| `direction` | Mean wave direction (coming from, clockwise from true north) | ° |

### Quality control

`qc_nowphas(raw, max_hs=25.0, calm_hs=0.25)` returns the clean table and a
report of how many values each step changed.

| Step | Rule |
|---|---|
| Missing and special codes | Height 99.99, period 999.9, direction or count 9999 become NaN, as do the special values 66.66 / 666.6 (calm) and 77.77 / 777.7 (not a high wave) |
| Missing records | Flag 9999 sets the whole record to NaN |
| Unrealistic heights | `hs > max_hs` sets that record's heights and periods to NaN |
| Calm seas | Direction code 6666 (used until 1999), flag 66, or `hs <= calm_hs` marks the record as calm and sets the direction to NaN. From 2000 NOWPHAS lists a direction even in calm seas. A boolean `calm` column keeps the information |

The clean table can be passed directly to `find_storms`.

From the command line:

```bash
pycoastkit hasaki download 1987-2022 -d nowphas_kashima
pycoastkit hasaki qc nowphas_kashima -o hasaki_waves.csv
```

## Beach profiles: HORS

The Hasaki Oceanographical Research Station (HORS, PARI) surveys a profile
along its pier from −115 m to +385 m every 5 m: on weekdays from 1986 to
March 2011, and weekly since then (Banno et al., 2020). Elevations refer to
the Hasaki Port datum.

| Level | Elevation | Constant |
|---|---|---|
| Mean high water springs (MHWS) | 1.25 m | `pck.hasaki.HASAKI_MHWS_M` |
| Mean sea level (MSL) | 0.65 m | `pck.hasaki.HASAKI_MSL_M` |

The data are distributed by PARI
([pari.mpat.go.jp/bdhome](https://pari.mpat.go.jp/bdhome/)). Request or
download them there and check the terms of use.

- `read_hors_profiles(path, units="cm")` reads a CSV with a `date` column and
  one column per position (`-115m` to `385m`, or plain numbers) and converts
  centimetres to metres.
- `hasaki_beach_state(profiles, water_level=1.25, sigma=2.0, volume_zone=(-40, 60))`
  runs the standard chain in one call: smoothing, shoreline at MHWS (seaward
  crossing) and beach volume. It returns `shoreline` and `volume`, ready for
  `storm_beach_response`.
