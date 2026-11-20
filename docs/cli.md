# Command line

Installing the package adds a `pycoastkit` command. Add `-h` to any command
for its options.

```bash
pycoastkit --version
pycoastkit -h
```

## Storms

Find storms in any table with a time column and an Hs column (CSV or
parquet):

```bash
pycoastkit storms waves.csv -o storms.csv
pycoastkit storms waves.csv --clusters -o events.csv
pycoastkit storms buoy.csv --hs-column Hm0 --hs-threshold 2.0 --peak-threshold 3.5
```

| Option | Default | Meaning |
|---|---|---|
| `--time-column` | `time` | Name of the time column |
| `--hs-column` | `hs` | Name of the Hs column |
| `--hs-threshold` | 1.5 | Storm Hs threshold [m] |
| `--peak-threshold` | 2.5 | Hs the peak must reach [m] |
| `--min-duration` | 6 | Minimum duration [h] |
| `--min-separation` | 48 | Storms closer than this form a cluster [h] |
| `--clusters` | off | Output one row per independent event |
| `-o`, `--output` | screen | Save as `.csv` or `.parquet` |

## Hasaki data

```bash
pycoastkit hasaki download 1987-2022 -d nowphas_kashima    # NOWPHAS Kashima, 2-hourly
pycoastkit hasaki download 2010 --interval 20min           # 20-minute statistics
pycoastkit hasaki qc nowphas_kashima -o hasaki_waves.csv    # read + quality control
```
