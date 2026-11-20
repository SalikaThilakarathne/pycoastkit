"""pycoastkit - a toolkit for sandy coasts: storms, beach profiles, shorelines,
sandbars, erosion, recovery and vulnerability.

Modules (all available after ``import pycoastkit as pck``)
-----------------------------------------------------------
``pck.storms``         find storms in a wave record, group them into clusters
``pck.beach``          beach profiles: smoothing, shoreline-relative coordinates, volumes, slopes
``pck.shoreline``      shoreline position at any water level, foreshore slope, shoreline QC
``pck.sandbars``       sandbar detection and bar configuration (profile type)
``pck.impacts``        beach change across each storm (shoreline retreat, volume loss)
``pck.recovery``       beach recovery after storms
``pck.vulnerability``  erosion classes, beach vulnerability index, susceptibility index, return periods
``pck.waves``          sea-state parameters, rogue waves, energy flux, storm surge
``pck.skill``          model skill scores
``pck.plot``           figures
``pck.hasaki``         Hasaki (Japan) wave and beach-profile data

The most used functions are also available directly, e.g. ``pck.find_storms``.

Copyright (c) 2026 Salika Thilakarathne, Helmholtz-Zentrum Hereon. MIT licence.
"""

__version__ = "0.1.0"
__author__ = "Salika Thilakarathne"

from . import (  # noqa: F401  (pck.storms, pck.plot, ...)
    beach,
    hasaki,
    impacts,
    plot,
    recovery,
    sandbars,
    shoreline,
    skill,
    storms,
    vulnerability,
    waves,
)
from .beach import (
    beach_volume,
    cut_and_fill,
    profile_slope,
    shoreline_relative_profiles,
    smooth_profiles,
)
from .impacts import storm_beach_response, survey_after, survey_before
from .recovery import iqr_outliers, post_storm_conditions, storm_recovery
from .sandbars import bar_height, bar_state, find_sandbars, sandbar_table
from .shoreline import (
    flag_shoreline_outliers,
    foreshore_slope,
    shoreline_position,
    shoreline_positions,
)
from .skill import skill_by_quantile, skill_scores, skill_table
from .storms import (
    StormCriteria,
    add_storm_energy,
    add_storm_wave_statistics,
    find_storms,
    storm_clusters,
    storm_power,
    storms_per_month,
    storms_per_year,
)
from .vulnerability import (
    add_vulnerability_index,
    beach_vulnerability_index,
    erosion_class,
    return_periods,
    susceptibility_index,
)
from .waves import (
    SpectralSettings,
    individual_wave_statistics,
    spectral_parameters,
    storm_surge,
    wave_energy_flux,
    wavenumber,
)

__all__ = [
    "__version__",
    # modules
    "storms", "beach", "shoreline", "sandbars", "impacts", "recovery",
    "vulnerability", "waves", "skill", "plot", "hasaki",
    # storms
    "StormCriteria", "find_storms", "storm_clusters", "storm_power",
    "add_storm_wave_statistics", "add_storm_energy", "storms_per_month", "storms_per_year",
    # beach
    "smooth_profiles", "shoreline_relative_profiles", "beach_volume", "cut_and_fill",
    "profile_slope",
    # shoreline
    "shoreline_position", "shoreline_positions", "foreshore_slope", "flag_shoreline_outliers",
    # sandbars
    "find_sandbars", "sandbar_table", "bar_state", "bar_height",
    # impacts and recovery
    "storm_beach_response", "survey_before", "survey_after",
    "storm_recovery", "post_storm_conditions", "iqr_outliers",
    # vulnerability
    "erosion_class", "beach_vulnerability_index", "add_vulnerability_index",
    "susceptibility_index", "return_periods",
    # waves
    "SpectralSettings", "spectral_parameters", "individual_wave_statistics", "wavenumber",
    "wave_energy_flux", "storm_surge",
    # skill
    "skill_scores", "skill_table", "skill_by_quantile",
]
