import numpy as np
import pandas as pd
import pytest

import pycoastkit as pck


def hourly(values, start="2001-01-01"):
    index = pd.date_range(start, periods=len(values), freq="h")
    return pd.DataFrame({"hs": np.asarray(values, dtype=float)}, index=index)


def test_single_individual_storm():
    hs = [1.0] * 5 + [2.0] * 3 + [3.0] * 4 + [1.0] * 10
    storms = pck.find_storms(hourly(hs))
    assert len(storms) == 1
    s = storms.iloc[0]
    assert s["duration_h"] == 7          # 7 hourly samples above 1.5 m
    assert s["peak_hs"] == 3.0
    assert s["kind"] == "individual"
    assert s["storm_power"] == pytest.approx(9.0 * 7)
    assert s["start_time"] == pd.Timestamp("2001-01-01 05:00")
    assert s["end_time"] == pd.Timestamp("2001-01-01 11:00")


def test_too_short_too_weak_and_empty():
    assert pck.find_storms(hourly([1.0] * 3 + [3.0] * 5 + [1.0] * 5)).empty   # 5 h < 6 h
    assert pck.find_storms(hourly([1.0] * 3 + [2.0] * 12 + [1.0] * 5)).empty  # peak < 2.5
    empty = pck.find_storms(hourly([1.0] * 10))
    assert "cluster_id" in empty.columns


def test_clusters():
    calm = [1.0]
    hs = calm * 2 + [3.0] * 8 + calm * 10 + [4.0] * 8 + calm * 80 + [3.0] * 8 + calm * 5
    storms = pck.find_storms(hourly(hs))
    assert list(storms["kind"]) == ["clustered", "clustered", "individual"]
    assert list(storms["cluster_id"]) == [1, 1, 2]
    assert storms["gap_before_h"].iloc[1] == 11
    clusters = pck.storm_clusters(storms)
    assert len(clusters) == 2
    first = clusters.iloc[0]
    assert first["n_storms"] == 2
    assert first["duration_h"] == 16
    assert first["peak_hs"] == 4.0
    assert first["storm_power"] == pytest.approx(9 * 8 + 16 * 8)


def test_nan_and_data_gap_split_storms():
    hs = [1.0] * 2 + [3.0] * 8 + [np.nan] + [3.0] * 8 + [1.0] * 2
    assert len(pck.find_storms(hourly(hs))) == 2
    df = hourly([3.0] * 16)
    df = df.drop(df.index[8:10])  # 2-hour hole in the record
    assert len(pck.find_storms(df, sampling_interval_h=1)) == 2


def test_two_hourly_data():
    index = pd.date_range("2001-01-01", periods=12, freq="2h")
    hs = pd.Series([1, 3, 3, 3, 1, 1, 1, 1, 1, 1, 1, 1], index=index, dtype=float)
    storms = pck.find_storms(hs)
    assert storms["duration_h"].iloc[0] == 6


def test_criteria_validation():
    with pytest.raises(ValueError):
        pck.StormCriteria(hs_threshold=3, peak_threshold=2)


def test_wave_statistics_and_counts():
    hs = [1.0] * 5 + [3.0] * 8 + [1.0] * 5
    waves = hourly(hs)
    waves["t0"] = np.arange(len(hs), dtype=float)
    waves["dir"] = [350.0, 10.0] * 9
    storms = pck.add_storm_wave_statistics(pck.find_storms(waves), waves,
                                          {"t0": ["mean", "max"], "dir": "circmean"})
    assert storms["max_t0"].iloc[0] == 12
    assert storms["mean_t0"].iloc[0] == pytest.approx(8.5)
    assert min(storms["mean_dir"].iloc[0], 360 - storms["mean_dir"].iloc[0]) < 1e-6
    assert pck.storms_per_month(storms).sum() == 1
    assert pck.storms_per_year(storms).loc[2001] == 1


def test_everything_is_reachable_from_one_import():
    assert callable(pck.plot.plot_storm_timeline)
    assert callable(pck.hasaki.read_nowphas)
    assert pck.storms.find_storms is pck.find_storms
    for name in pck.__all__:
        assert hasattr(pck, name), name
