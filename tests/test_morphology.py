"""Sandbars, shoreline variants, shoreline-relative profiles, recovery, vulnerability."""

import numpy as np
import pandas as pd
import pytest

import pycoastkit as pck

X = np.arange(-115, 386, 5.0)


def barred_profile(shore=0.0, bars=((120.0, 0.6, 20.0), (260.0, 1.0, 30.0)), slope=0.008,
                   level=1.25):
    """Planar beach crossing `level` at `shore`, plus Gaussian bars (x, height, width)."""
    z = level - slope * (X - shore)
    for xc, h, w in bars:
        z = z + h * np.exp(-0.5 * ((X - shore - xc) / w) ** 2)
    return z


def test_bar_height_on_chord():
    # crest 1 m above the line joining troughs at the same depth
    assert pck.bar_height(0, 10, 20, -2.0, -1.0, -2.0) == pytest.approx(1.0)
    # sloping chord: line at x=10 is -2.5, crest at -1 -> 1.5 m
    assert pck.bar_height(0, 10, 20, -2.0, -1.0, -3.0) == pytest.approx(1.5)


def test_find_sandbars_inner_and_outer():
    bars = pck.find_sandbars(X, barred_profile(), smooth_sigma=0)
    assert list(bars["zone"]) == ["inner", "outer"]
    assert bars["crest_x"].iloc[0] == pytest.approx(120, abs=5)
    assert bars["crest_x"].iloc[1] == pytest.approx(260, abs=5)
    assert (bars["height"] > 0.24).all()
    assert bars["depth"].iloc[0] == pytest.approx(1.25 - bars["crest_z"].iloc[0])
    assert (bars[["slope_land", "slope_sea"]] > 0).all().all()


def test_find_sandbars_thresholds_and_unbarred():
    assert pck.find_sandbars(X, barred_profile(bars=())).empty
    small = pck.find_sandbars(X, barred_profile(bars=((120, 0.1, 25),)), smooth_sigma=0)
    assert small.empty
    near = pck.find_sandbars(X, barred_profile(bars=((30, 0.8, 10),)), smooth_sigma=0)
    assert near.empty  # closer than 50 m to the shoreline
    every = pck.find_sandbars(X, barred_profile(bars=((30, 0.8, 10),)), smooth_sigma=0,
                              keep_all=True)
    assert len(every) == 1


def test_sandbar_table_and_bar_state():
    days = pd.date_range("2001-01-01", periods=4, freq="D")
    configs = [(), ((120, 0.6, 20),), ((260, 1.0, 30),), ((120, 0.6, 20), (260, 1.0, 30))]
    profiles = pd.DataFrame([barred_profile(bars=c) for c in configs], index=days, columns=X)
    table = pck.sandbar_table(profiles, smooth_sigma=0)
    state = pck.bar_state(table, times=profiles.index)
    assert list(state["profile_type"]) == [1, 2, 3, 4]
    assert np.isnan(state["inner_height"].iloc[0])
    assert state["outer_crest_x"].iloc[3] == pytest.approx(260, abs=5)


def test_shoreline_relative_profiles_and_volumes():
    days = pd.date_range("2001-01-01", periods=2, freq="D")
    profiles = pd.DataFrame([barred_profile(shore=10.0), barred_profile(shore=-7.5)],
                            index=days, columns=X)
    shore = pck.shoreline_positions(profiles, 1.25)
    assert np.allclose(shore, [10.0, -7.5], atol=0.2)
    rel = pck.shoreline_relative_profiles(profiles, shore)
    # same shape relative to the shoreline -> identical relative profiles
    assert np.allclose(rel.iloc[0], rel.iloc[1], atol=0.05, equal_nan=True)
    inner = pck.beach_volume(rel, 20, 170, base=-10.0)
    assert inner.iloc[0] == pytest.approx(inner.iloc[1], rel=1e-3)
    bars = pck.find_sandbars(rel.columns, rel.iloc[1], smooth_sigma=0)
    assert bars["crest_x"].iloc[0] == pytest.approx(120, abs=5)


def test_seaward_crossing_and_foreshore_slope():
    z = barred_profile(bars=((150, 2.0, 15),))  # bar emerges above 1.25 m
    assert pck.shoreline_position(X, z, 1.25, "landward") == pytest.approx(0, abs=0.5)
    assert pck.shoreline_position(X, z, 1.25, "seaward") > 150
    days = pd.date_range("2001", periods=1)
    planar = pd.DataFrame([1.25 - 0.02 * X], index=days, columns=X)
    assert pck.foreshore_slope(planar, 1.25, -0.2).iloc[0] == pytest.approx(0.02)
    assert pck.profile_slope(planar, 0, 150).iloc[0] == pytest.approx(0.02)


def test_cut_and_fill():
    before = pd.Series(np.zeros(11), index=np.arange(0, 51, 5.0))
    after = before.copy()
    after.iloc[1:4] = -1.0   # 15 m wide hole: cut 15 m3/m (trapezoid)
    after.iloc[7:9] = 0.5
    result = pck.cut_and_fill(before, after)
    assert result["cut"] == pytest.approx(15.0)
    assert result["fill"] == pytest.approx(5.0)
    assert result["net_loss"] == pytest.approx(10.0)


def test_storm_recovery():
    days = pd.date_range("2001-01-01", periods=30, freq="D")
    shore = pd.Series(50.0, index=days)
    shore.loc["2001-01-06":] = 40.0                       # 10 m retreat in the storm
    shore.loc["2001-01-16":] = 46.0                       # 6 m back 10 days later
    storms = pd.DataFrame({"start_time": [pd.Timestamp("2001-01-04 12:00")],
                           "end_time": [pd.Timestamp("2001-01-05 00:00")],
                           "gap_after_h": [500.0]})
    response = pck.storm_beach_response(storms, shore.rename("shoreline"))
    rec = pck.storm_recovery(response, shore.rename("shoreline"), n_days=10)
    row = rec.iloc[0]
    assert row["shoreline_loss"] == 10
    assert row["shoreline_recovery"] == 6
    assert row["shoreline_recovery_ratio"] == pytest.approx(0.6)
    assert bool(row["undisturbed"])
    capped = pck.storm_recovery(response, shore.rename("shoreline"), min_loss=20)
    assert np.isnan(capped["shoreline_recovery_ratio"].iloc[0])


def test_post_storm_conditions_and_iqr():
    idx = pd.date_range("2001-01-01", periods=24 * 20, freq="h")
    waves = pd.DataFrame({"hs": np.where(idx < "2001-01-05", 3.0, 1.0)}, index=idx)
    storms = pd.DataFrame({"end_time": [pd.Timestamp("2001-01-05")]})
    out = pck.post_storm_conditions(storms, waves, {"hs": ["mean", "max"]}, n_days=5)
    assert out["post_mean_hs"].iloc[0] == pytest.approx(1.0)
    assert pck.iqr_outliers([1, 1.1, 0.9, 1.0, 9.0]).tolist() == [False, False, False, False, True]


def test_vulnerability_classes():
    assert list(pck.erosion_class([-3, 0, 2, 5, 9.9, 14, 40], 5)) == [1, 1, 2, 3, 3, 4, 5]
    assert pck.beach_vulnerability_index(12.0, 25.0) == pytest.approx((4 + 4) / 2)
    assert list(pck.vulnerability.classify_by_thresholds([-1, 1, 2, 5, 8])) == [1, 2, 3, 4, 5]
    response = pd.DataFrame({"shoreline_loss": [-2, 6, 20], "volume_loss": [-5, 15, 50]})
    out = pck.add_vulnerability_index(response)
    assert list(out["bvi"]) == [1.0, 3.0, 5.0]


def test_susceptibility_index():
    indicators = pd.DataFrame({"shoreline": [10, 20, 30, 40, 50],
                               "inner_volume": [100, 200, 300, 400, 500]})
    # a wider beach (shoreline further seaward) and more sand make it LESS susceptible
    out = pck.susceptibility_index(indicators, {"shoreline": 2, "inner_volume": 1},
                                   direction={"shoreline": -1, "inner_volume": -1})
    assert list(out["susceptibility"]) == [5, 4, 3, 2, 1]
    assert list(out["class_shoreline"]) == [5, 4, 3, 2, 1]
    with pytest.raises(KeyError):
        pck.susceptibility_index(indicators, {"slope": 1})


def test_return_periods():
    when = pd.to_datetime(["2001-03-01", "2001-09-01", "2002-05-01", "2003-01-01"])
    table = pck.return_periods(pd.Series([3.0, 9.0, 4.0, 6.0], index=when))
    assert list(table["annual_max"]) == [9.0, 6.0, 4.0]
    assert list(table["return_period_years"]) == pytest.approx([4.0, 2.0, 4 / 3])


def test_energy_flux_and_storm_energy_and_surge():
    deep = pck.wave_energy_flux(2.0, 10.0)
    assert deep == pytest.approx(1025 * 9.81**2 * 4 * 10 / (64 * np.pi))
    # shallow water: group speed -> sqrt(g h)
    shallow = pck.wave_energy_flux(1.0, 60.0, depth_m=2.0)
    assert shallow == pytest.approx(1025 * 9.81 / 16 * np.sqrt(9.81 * 2.0), rel=0.02)

    idx = pd.date_range("2001-01-01", periods=10, freq="h")
    waves = pd.DataFrame({"hs": 2.0, "ts": 10.0}, index=idx)
    storms = pd.DataFrame({"start_time": [idx[0]], "end_time": [idx[-1]]})
    out = pck.add_storm_energy(storms, waves)
    assert out["energy_mj_per_m"].iloc[0] == pytest.approx(deep * 9 * 3600 / 1e6)
    two_hourly = waves.iloc[::2]
    out2 = pck.add_storm_energy(pd.DataFrame({"start_time": [idx[0]], "end_time": [idx[8]]}),
                                two_hourly)
    assert out2["energy_mj_per_m"].iloc[0] == pytest.approx(deep * 8 * 3600 / 1e6)

    observed = pd.Series([1.0, 0.5, 2.0])
    tide = pd.Series([0.8, 0.9, 1.0])
    assert list(pck.storm_surge(observed, tide, clip_negative=True).round(2)) == [0.2, 0.0, 1.0]
