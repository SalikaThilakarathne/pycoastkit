# Waves

## Wave energy flux

`wave_energy_flux(hs, period, depth_m=None)` is the wave power per metre of
wave crest [W/m] from linear wave theory:

$$
P = E \, c_g, \qquad E = \frac{\rho g H_s^2}{16}
$$

In deep water (`depth_m=None`) the group speed is $c_g = gT/(4\pi)$, giving

$$
P = \frac{\rho g^2 H_s^2 T}{64 \pi} \approx 490 \, H_s^2 \, T \ \ \mathrm{W/m}.
$$

Give `depth_m` for intermediate or shallow water; the group speed then
follows from the dispersion relation solved by `wavenumber(period, depth)`.
Use the energy period if it is available; the significant or peak period is
a common substitute.

## Storm surge

`storm_surge(observed, predicted_tide, clip_negative=False)` is the observed
water level minus the predicted astronomical tide. With `clip_negative=True`
only positive surge is kept.

## Sea state from surface elevation

For high-frequency records of the sea surface (wave buoys, radar or laser
gauges, typically 2 to 4 Hz), these functions describe the waves within a
storm in more detail than Hs alone.

### Spectral parameters

`spectral_parameters(elevation, SpectralSettings(...))` removes a linear
trend and estimates the spectrum $S(f)$ with Welch's method (Hann window).
Spectral moments $m_n = \int f^n S(f)\,df$ are taken over `band_hz`. Use a
continuous record without gaps, typically 20 to 30 minutes long.

| Key | Definition |
|---|---|
| `hm0` | $4\sqrt{m_0}$, spectral significant wave height [m] |
| `tm01`, `tm02` | $m_0/m_1$ and $\sqrt{m_0/m_2}$, mean periods [s] |
| `tp` | Peak period from the $S^4$-weighted spectrum, more robust than the maximum [s] |
| `kp`, `wavelength` | Peak wavenumber from the linear dispersion relation, and $2\pi/k_p$ |
| `steepness` | $\sqrt{2 m_0}\, k_p$ |
| `relative_depth`, `ursell` | $h/L$ and steepness$/(h/L)^3$, measures of shallow-water nonlinearity |
| `spectral_width` | Longuet-Higgins width $\sqrt{m_0 m_2/m_1^2 - 1}$ |
| `goda_qp` | Goda peakedness $2\int f S^2 df / m_0^2$ |
| `bfi` | $\sqrt{2}\cdot$ steepness $\cdot Q_p$, a Benjamin-Feir index proxy |
| `crest_trough_correlation` | Spectral correlation at half the mean period |
| `low_freq_fraction`, `high_freq_fraction` | Share of energy in the swell and wind-sea bands |
| `skewness`, `excess_kurtosis` | Shape of the surface-elevation distribution (0 and 0 for a linear Gaussian sea) |
| `variance_closure` | Spectral variance over time-domain variance; a quality check that should be close to 1 |

The predictor set follows Häfner, Gemmrich and Jochum (2021).

### Individual waves

`individual_wave_statistics(elevation, sampling_hz=4.0, n_waves=100)`
performs a zero-upcrossing analysis of the first `n_waves` valid waves.

| Key | Meaning |
|---|---|
| `status` | `"ok"`, or the reason the analysis failed |
| `h13`, `hmax`, `cmax` | Mean of the highest third of waves, highest wave, highest crest [m] |
| `abnormality_index` | $H_{\max}/H_{1/3}$; `rogue_wave` is True when it is at least 2 |
| `crest_index` | $C_{\max}/H_{1/3}$; `rogue_crest` is True when it is at least 1.25 |
| `mean_period`, `start_s`, `end_s` | Mean zero-crossing period and the time span analysed |
