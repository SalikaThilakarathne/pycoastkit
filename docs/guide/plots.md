# Plots

Figures live in `pck.plot`. Every function accepts `ax=` for multi-panel
figures and returns the axis. Importing the package leaves matplotlib
settings unchanged; call `pck.plot.use_style()` for a compact journal style.
Individual storms are drawn in grey and storm clusters in magenta.

| Function | Shows |
|---|---|
| `plot_storm_timeline(waves, storms, criteria, start, end)` | Hs with storms shaded and both thresholds |
| `plot_storm_counts(storms, by="year" or "month")` | Stacked bars of individual and clustered storms (trend or seasonality) |
| `plot_profiles(profiles, start, end, water_level, shoreline)` | Overlaid surveys, to check outliers or storm erosion |
| `plot_sandbars(x, elevation, bars, reference_level)` | One profile with its bar crests, troughs and trough lines |
| `plot_beach_response(response, x="storm_power", y="shoreline_loss")` | Storm forcing against beach change |
| `plot_density_scatter(observed, predicted)` | Hexbin density, 1:1 line, matched percentiles and a skill box |
| `plot_wave_rose(directions_deg)` | Frequency rose of wave directions |

```python
pck.plot.use_style()
ax = pck.plot.plot_storm_timeline(waves, storms, start="2006-10-01", end="2006-11-15")
ax.figure.savefig("storms_2006.png", dpi=300)
```

The colours follow a fixed palette, available as `pck.plot.PALETTE`.
