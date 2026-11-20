"""Sea-state parameters from a sea-surface-elevation record (e.g. a 4 Hz wave buoy
or pressure/laser gauge record during a storm).

* :func:`spectral_parameters` - Welch spectrum -> Hm0, periods, steepness,
  peakedness, Benjamin-Feir index proxy, Ursell number, ...
* :func:`individual_wave_statistics` - zero-upcrossing analysis -> H1/3, Hmax,
  abnormality index and rogue-wave flags.

The spectral predictor set follows Häfner, Gemmrich & Jochum (2021),
"Real-world rogue wave probabilities", Scientific Reports 11, 10084.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import signal
from scipy.optimize import brentq

__all__ = ["SpectralSettings", "spectral_parameters", "individual_wave_statistics",
           "wavenumber", "wave_energy_flux", "storm_surge"]

GRAVITY = 9.81
_trapezoid = getattr(np, "trapezoid", None) or getattr(np, "trapz")


def wavenumber(period_s: float, depth_m: float, gravity: float = GRAVITY) -> float:
    """Wavenumber k [rad/m] from the linear dispersion relation
    ``(2 pi / T)^2 = g k tanh(k h)``."""
    if not np.isfinite(period_s) or period_s <= 0:
        return np.nan
    omega2 = (2.0 * np.pi / period_s) ** 2
    return float(brentq(lambda k: gravity * k * np.tanh(k * depth_m) - omega2, 1e-10, 100.0))


def wave_energy_flux(hs, period, depth_m=None, rho: float = 1025.0, gravity: float = GRAVITY):
    """Wave energy flux (wave power) per metre of wave crest [W/m].

    ``P = E * cg`` with energy density ``E = rho g Hs² / 16`` and group speed
    ``cg`` from linear wave theory. In deep water (``depth_m=None``)
    ``cg = g T / (4 pi)``, giving ``P = rho g² Hs² T / (64 pi)``
    (about 490 Hs² T W/m). Use the energy period Te if available; peak or
    significant period is a common substitute.
    """
    hs = np.asarray(hs, dtype=float)
    period = np.asarray(period, dtype=float)
    energy = rho * gravity * hs**2 / 16.0
    if depth_m is None:
        cg = gravity * period / (4.0 * np.pi)
    else:
        k = np.vectorize(lambda t: wavenumber(t, depth_m, gravity))(period)
        kh = k * depth_m
        c = 2.0 * np.pi / (period * k)
        cg = 0.5 * c * (1.0 + 2.0 * kh / np.sinh(2.0 * kh))
    flux = energy * cg
    return flux if flux.ndim else float(flux)


def storm_surge(observed, predicted_tide, clip_negative: bool = False):
    """Storm surge = observed water level - predicted (astronomical) tide [m].

    ``clip_negative=True`` sets negative surge (set-down) to 0.
    Works on arrays or aligned pandas Series.
    """
    surge = observed - predicted_tide
    if clip_negative:
        surge = surge.clip(lower=0) if hasattr(surge, "clip") else np.maximum(surge, 0)
    return surge


@dataclass(frozen=True)
class SpectralSettings:
    """Settings for :func:`spectral_parameters`.

    Parameters
    ----------
    sampling_hz : record sampling frequency [Hz]
    water_depth_m : local water depth [m] (for wavenumber, steepness, Ursell number)
    segment_s : Welch segment length [s]; longer = finer frequency resolution
    overlap : Welch segment overlap (0-1)
    band_hz : frequency band used for the spectral moments [Hz]
    low_band_hz, high_band_hz : bands for the swell/wind-sea energy fractions
    nfft : FFT length (None = next power of two >= segment length)
    """

    sampling_hz: float = 4.0
    water_depth_m: float = 20.0
    segment_s: float = 180.0
    overlap: float = 0.5
    band_hz: tuple = (0.04, 1.0)
    low_band_hz: tuple = (0.05, 0.10)
    high_band_hz: tuple = (0.25, 1.0)
    nfft: int | None = None
    _cache: dict = field(default_factory=dict, init=False, repr=False, compare=False)

    def _welch(self):
        if not self._cache:
            nperseg = int(round(self.segment_s * self.sampling_hz))
            nfft = self.nfft or 1 << int(np.ceil(np.log2(nperseg)))
            f = np.fft.rfftfreq(nfft, 1.0 / self.sampling_hz)
            self._cache.update(
                nperseg=nperseg,
                noverlap=int(round(nperseg * self.overlap)),
                nfft=nfft,
                band=(f >= self.band_hz[0]) & (f <= self.band_hz[1]),
                low=(f >= self.low_band_hz[0]) & (f <= self.low_band_hz[1]),
                high=(f >= self.high_band_hz[0]) & (f <= self.high_band_hz[1]),
            )
        return self._cache


def spectral_parameters(elevation, settings: SpectralSettings | None = None) -> dict:
    """Sea-state parameters from one continuous record (typically 20-30 min).

    The record is linearly detrended and its spectrum estimated with Welch's
    method (Hann window).

    Returns
    -------
    dict with
        ``hm0`` [m] 4 sqrt(m0); ``tm01``, ``tm02`` [s] mean periods;
        ``tp`` [s] peak period (robust, from the S^4-weighted spectrum);
        ``kp`` [rad/m], ``wavelength`` [m] at the peak;
        ``steepness`` sqrt(2 m0) kp; ``relative_depth`` h / L;
        ``ursell`` steepness / (h/L)^3; ``spectral_width`` (Longuet-Higgins);
        ``goda_qp`` Goda peakedness; ``bfi`` sqrt(2) steepness Qp (BFI proxy);
        ``crest_trough_correlation``; ``low_freq_fraction``,
        ``high_freq_fraction`` energy in ``low_band_hz``/``high_band_hz``;
        ``skewness``, ``excess_kurtosis`` of the surface elevation;
        ``variance_closure`` spectral / time-domain variance (QC: should be ~1);
        ``m0, m1, m2, m4`` spectral moments.
    """
    settings = settings or SpectralSettings()
    w = settings._welch()
    eta = np.asarray(elevation, dtype=float)
    if eta.ndim != 1 or not np.isfinite(eta).all():
        raise ValueError("elevation must be one-dimensional and contain no NaN")
    if eta.size < w["nperseg"]:
        raise ValueError("record is shorter than one Welch segment")

    eta = signal.detrend(eta, type="linear")
    f, S = signal.welch(eta, fs=settings.sampling_hz, window="hann", nperseg=w["nperseg"],
                        noverlap=w["noverlap"], nfft=w["nfft"], detrend=False,
                        scaling="density")
    fb, Sb = f[w["band"]], S[w["band"]]
    m0, m1, m2, m4 = (float(_trapezoid(fb**n * Sb, fb)) for n in (0, 1, 2, 4))

    tp = float(_trapezoid(Sb**4, fb) / _trapezoid(fb * Sb**4, fb))
    h = settings.water_depth_m
    kp = wavenumber(tp, h)
    wavelength = 2.0 * np.pi / kp
    steepness = np.sqrt(2.0 * m0) * kp
    relative_depth = h / wavelength
    qp = 2.0 * _trapezoid(fb * Sb**2, fb) / m0**2

    tm01 = m0 / m1
    phase = np.pi * fb * tm01  # correlation at half the mean period
    rho = np.hypot(_trapezoid(Sb * np.cos(phase), fb), _trapezoid(Sb * np.sin(phase), fb)) / m0

    anomaly = eta - eta.mean()
    variance = float(np.mean(anomaly**2))
    std = np.sqrt(variance)

    return {
        "hm0": 4.0 * np.sqrt(m0),
        "tm01": tm01,
        "tm02": float(np.sqrt(m0 / m2)),
        "tp": tp,
        "kp": kp,
        "wavelength": wavelength,
        "steepness": float(steepness),
        "relative_depth": float(relative_depth),
        "ursell": float(steepness / relative_depth**3),
        "spectral_width": float(np.sqrt(max(m0 * m2 / m1**2 - 1.0, 0.0))),
        "goda_qp": float(qp),
        "bfi": float(np.sqrt(2.0) * steepness * qp),
        "crest_trough_correlation": float(rho),
        "low_freq_fraction": float(_trapezoid(S[w["low"]], f[w["low"]]) / m0),
        "high_freq_fraction": float(_trapezoid(S[w["high"]], f[w["high"]]) / m0),
        "skewness": float(np.mean(anomaly**3) / std**3) if std > 0 else np.nan,
        "excess_kurtosis": float(np.mean(anomaly**4) / std**4 - 3.0) if std > 0 else np.nan,
        "variance_closure": float(_trapezoid(S, f) / variance) if variance > 0 else np.nan,
        "m0": m0,
        "m1": m1,
        "m2": m2,
        "m4": m4,
    }


def individual_wave_statistics(elevation, sampling_hz: float = 4.0, n_waves: int = 100,
                               period_range_s: tuple = (1.0, 30.0)) -> dict:
    """Zero-upcrossing statistics of the first ``n_waves`` valid waves.

    The record is linearly detrended and cut at zero upcrossings (positions
    interpolated between samples). A wave counts when its period is inside
    ``period_range_s`` and its height and crest are positive.

    Returns
    -------
    dict with
        ``status`` - ``"ok"`` or the reason it failed;
        ``n_waves`` - waves found (up to ``n_waves``);
        on success also ``h13`` [m] (mean of the highest third), ``hmax``,
        ``cmax`` [m], ``mean_period`` [s], ``abnormality_index`` Hmax/H1/3,
        ``crest_index`` Cmax/H1/3, ``rogue_wave`` (AI >= 2), ``rogue_crest``
        (CI >= 1.25), and ``start_s``/``end_s`` of the analysed waves.
    """
    eta = np.asarray(elevation, dtype=float)
    if eta.ndim != 1 or not np.isfinite(eta).all():
        raise ValueError("elevation must be one-dimensional and contain no NaN")
    eta = signal.detrend(eta, type="linear")

    up = np.flatnonzero((eta[:-1] < 0.0) & (eta[1:] >= 0.0))
    if up.size < 2:
        return {"status": "no complete waves", "n_waves": 0}

    # sub-sample crossing positions
    position = up - eta[up] / (eta[up + 1] - eta[up])
    heights, crests, periods, starts, ends = [], [], [], [], []
    for a, b, pa, pb in zip(up[:-1], up[1:], position[:-1], position[1:]):
        period = (pb - pa) / sampling_hz
        if not (period_range_s[0] <= period <= period_range_s[1]):
            continue
        wave = eta[a + 1:b + 1]
        crest = wave.max()
        height = crest - wave.min()
        if wave.size < 2 or height <= 0 or crest <= 0:
            continue
        heights.append(height)
        crests.append(crest)
        periods.append(period)
        starts.append(pa)
        ends.append(pb)
        if len(heights) == n_waves:
            break

    if len(heights) < n_waves:
        return {"status": f"fewer than {n_waves} valid waves", "n_waves": len(heights)}

    heights = np.asarray(heights)
    n_third = int(np.ceil(n_waves / 3.0))
    h13 = float(np.sort(heights)[-n_third:].mean())
    hmax, cmax = float(heights.max()), float(max(crests))
    return {
        "status": "ok",
        "n_waves": n_waves,
        "h13": h13,
        "hmax": hmax,
        "cmax": cmax,
        "mean_period": float(np.mean(periods)),
        "abnormality_index": hmax / h13,
        "crest_index": cmax / h13,
        "rogue_wave": bool(hmax / h13 >= 2.0),
        "rogue_crest": bool(cmax / h13 >= 1.25),
        "start_s": float(starts[0] / sampling_hz),
        "end_s": float(ends[-1] / sampling_hz),
    }
