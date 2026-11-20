import numpy as np
import pandas as pd
import pytest

import pycoastkit as pck

X = np.arange(-100, 301, 5.0)


def planar_profile(shoreline_x, slope=0.02, level=1.0):
    """Planar beach crossing `level` at `shoreline_x`."""
    return level - slope * (X - shoreline_x)


def profile_table(shorelines, start="2001-01-01"):
    index = pd.date_range(start, periods=len(shorelines), freq="D")
    data = [planar_profile(s) for s in shorelines]
    return pd.DataFrame(data, index=index, columns=[f"{int(x)}m" for x in X])


def test_shoreline_position_interpolates():
    assert pck.shoreline_position(X, planar_profile(52.5), 1.0) == pytest.approx(52.5)


def test_shoreline_landward_vs_seaward_with_emerged_bar():
    z = planar_profile(0.0)
    bar = (X >= 100) & (X <= 120)
    z[bar] = 1.5  # bar above water level, seaward of the beach face
    assert pck.shoreline_position(X, z, 1.0, "landward") == pytest.approx(0.0)
    assert pck.shoreline_position(X, z, 1.0, "seaward") > 115


def test_shoreline_positions_and_smoothing():
    profiles = profile_table([50, 45, 40])
    shore = pck.shoreline_positions(profiles, water_level=1.0)
    assert np.allclose(shore, [50, 45, 40])
    smooth = pck.smooth_profiles(profiles, sigma=2)
    assert np.allclose(pck.shoreline_positions(smooth, 1.0), [50, 45, 40], atol=0.5)
    profiles.iloc[0, 10] = np.nan
    smooth = pck.smooth_profiles(profiles)
    assert np.isnan(smooth.iloc[0, 10]) and np.isfinite(smooth.iloc[0, 11])


def test_beach_volume():
    profiles = profile_table([50, 40])  # 10 m retreat on a 0.02 slope
    vol = pck.beach_volume(profiles, x_min=-40, x_max=60, base=0.0)
    # parallel shift: volume difference = 10 m * 0.02 * 100 m = 20 m3/m
    assert vol.iloc[0] - vol.iloc[1] == pytest.approx(20.0)
    rel = pck.beach_volume(profiles, x_min=-40, x_max=60)  # base = lowest observed
    assert rel.iloc[1] == pytest.approx(0.0)


def test_flag_shoreline_outliers():
    values = np.full(30, 50.0) + np.sin(np.arange(30)) * 0.5
    values[15] = 80.0
    shore = pd.Series(values, index=pd.date_range("2001", periods=30, freq="D"))
    flags = pck.flag_shoreline_outliers(shore)
    assert flags["is_outlier"].iloc[15]
    assert flags["is_outlier"].sum() <= 3


def test_storm_beach_response():
    days = pd.date_range("2001-01-01", periods=10, freq="D")
    beach = pd.DataFrame({"shoreline": [50, 50, 50, np.nan, np.nan, 44, 44, 45, 45, 46],
                          "volume": [100, 100, 100, 99, 90, 88, 88, 89, 90, 90]}, index=days)
    storms = pd.DataFrame({"start_time": [pd.Timestamp("2001-01-04 06:00")],
                           "end_time": [pd.Timestamp("2001-01-05 18:00")]})
    out = pck.storm_beach_response(storms, beach)
    row = out.iloc[0]
    assert row["shoreline_pre_time"] == pd.Timestamp("2001-01-03")
    assert row["shoreline_post_time"] == pd.Timestamp("2001-01-06")
    assert row["shoreline_loss"] == 6
    assert row["volume_loss"] == 12
    far = pck.storm_beach_response(storms, beach, max_search_days=0, days_before=5)
    assert np.isnan(far["shoreline_loss"].iloc[0])
