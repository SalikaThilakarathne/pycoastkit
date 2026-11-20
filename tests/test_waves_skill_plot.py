import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

import pycoastkit as pck  # noqa: E402
from pycoastkit import plot  # noqa: E402


def sine(amplitude=1.0, period=8.0, minutes=30, fs=4.0):
    t = np.arange(int(minutes * 60 * fs)) / fs
    return amplitude * np.sin(2 * np.pi * t / period)


def test_spectral_parameters_of_a_sine():
    p = pck.spectral_parameters(sine(1.0, 8.0), pck.SpectralSettings(water_depth_m=30.0))
    assert p["hm0"] == pytest.approx(4 / np.sqrt(2), rel=0.03)
    assert p["tp"] == pytest.approx(8.0, rel=0.03)
    assert p["variance_closure"] == pytest.approx(1.0, abs=0.05)
    assert p["excess_kurtosis"] == pytest.approx(-1.5, abs=0.01)


def test_spectral_parameters_errors():
    eta = sine()
    eta[3] = np.nan
    with pytest.raises(ValueError):
        pck.spectral_parameters(eta)
    with pytest.raises(ValueError):
        pck.spectral_parameters(sine(minutes=1))


def test_wavenumber_limits():
    assert pck.wavenumber(8.0, 1000.0) == pytest.approx((2 * np.pi / 8) ** 2 / 9.81, rel=1e-6)
    assert pck.wavenumber(60.0, 1.0) == pytest.approx(2 * np.pi / 60 / np.sqrt(9.81), rel=0.01)


def test_individual_waves_and_rogue_flag():
    regular = pck.individual_wave_statistics(sine(0.5, 8.0))
    assert regular["status"] == "ok"
    assert regular["h13"] == pytest.approx(1.0, rel=0.01)
    assert regular["mean_period"] == pytest.approx(8.0, rel=0.01)
    assert regular["rogue_wave"] is False

    eta = sine(0.5, 8.0)
    t = np.arange(eta.size) / 4.0
    eta[(t >= 400) & (t < 408)] *= 3.0
    assert pck.individual_wave_statistics(eta)["rogue_wave"] is True
    assert pck.individual_wave_statistics(sine(minutes=2))["status"].startswith("fewer")


def test_skill():
    o = np.array([1.0, 2.0, 3.0, 4.0, np.nan])
    s = pck.skill_scores(o, o + 0.5)
    assert s["n"] == 4 and s["bias"] == pytest.approx(0.5) and s["rmse"] == pytest.approx(0.5)
    rng = np.random.default_rng(0)
    obs = rng.gamma(2, 1, 400)
    q = pck.skill_by_quantile(obs, obs + rng.normal(0, 0.1, 400))
    assert list(q.index) == ["Q1", "Q2", "Q3", "Q4"]
    idx = pd.date_range("2001", periods=50, freq="h")
    table = pck.skill_table(pd.DataFrame({"hs": obs[:50]}, index=idx),
                           pd.DataFrame({"hs": obs[:50] + 0.1}, index=idx))
    assert table.loc["hs", "bias"] == pytest.approx(0.1)


def test_plots_smoke():
    rng = np.random.default_rng(1)
    idx = pd.date_range("2001-01-01", periods=24 * 60, freq="h")
    hs = pd.Series(1 + np.abs(rng.normal(0, 0.6, idx.size)).cumsum() % 3.5, index=idx)
    waves = pd.DataFrame({"hs": hs, "dir": rng.uniform(0, 360, idx.size)})
    storms = pck.find_storms(waves, pck.StormCriteria(1.5, 2.5, 3, 48))
    assert not storms.empty
    plot.use_style()
    plot.plot_storm_timeline(waves, storms)
    plot.plot_storm_counts(storms, by="month")
    plot.plot_storm_counts(storms, by="year")
    x = np.arange(-100, 301, 5.0)
    profiles = pd.DataFrame([1 - 0.02 * (x - s) for s in (50, 45)], columns=x,
                            index=pd.date_range("2001", periods=2, freq="D"))
    plot.plot_profiles(profiles, water_level=1.0, shoreline=50.0)
    response = storms.assign(shoreline_loss=rng.normal(2, 3, len(storms)))
    plot.plot_beach_response(response)
    plot.plot_density_scatter(hs, hs + rng.normal(0, 0.2, hs.size))
    plot.plot_wave_rose(waves["dir"])
    plt.close("all")


def test_plot_sandbars_smoke():
    x = np.arange(-40, 341, 5.0)
    z = 1.25 - 0.008 * x + 0.8 * np.exp(-0.5 * ((x - 150) / 20) ** 2)
    bars = pck.find_sandbars(x, z)
    assert len(bars) == 1
    plot.plot_sandbars(x, z, bars, reference_level=1.25)
    plt.close("all")
