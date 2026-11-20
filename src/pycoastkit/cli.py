"""Command line: ``pycoastkit <command>`` (run ``pycoastkit -h`` for help)."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import __version__


def _read_table(path: Path, time_column: str):
    import pandas as pd

    if path.suffix.lower() == ".parquet":
        data = pd.read_parquet(path)
        if time_column in data.columns:
            data = data.set_index(time_column)
    else:
        data = pd.read_csv(path, index_col=time_column, parse_dates=True)
    data.index = pd.to_datetime(data.index)
    return data


def _write_table(table, path: Path) -> None:
    if path.suffix.lower() == ".parquet":
        table.to_parquet(path)
    else:
        table.to_csv(path, index=False)
    print(f"wrote {len(table):,} rows to {path.name}")


def _storms(args) -> None:
    from .storms import StormCriteria, find_storms, storm_clusters

    waves = _read_table(Path(args.waves), args.time_column)
    criteria = StormCriteria(args.hs_threshold, args.peak_threshold, args.min_duration,
                             args.min_separation)
    storms = find_storms(waves, criteria, hs_column=args.hs_column)
    table = storm_clusters(storms) if args.clusters else storms
    if args.output:
        _write_table(table, Path(args.output))
    else:
        print(table.to_string(index=False))
    n_clustered = int((storms["kind"] == "clustered").sum()) if len(storms) else 0
    print(f"\n{len(storms)} storms ({n_clustered} in clusters), "
          f"{storms['cluster_id'].nunique() if len(storms) else 0} independent events")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pycoastkit",
        description="pycoastkit: tools for sandy coasts (storms, beaches, Hasaki data).",
    )
    parser.add_argument("--version", action="version", version=f"pycoastkit {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("storms", help="find storms in an Hs time series (CSV or parquet)")
    p.add_argument("waves", help="table with a time column and an Hs column [m]")
    p.add_argument("-o", "--output", help="save the storm table (.csv or .parquet)")
    p.add_argument("--clusters", action="store_true",
                   help="output one row per independent event (clusters combined)")
    p.add_argument("--time-column", default="time")
    p.add_argument("--hs-column", default="hs")
    p.add_argument("--hs-threshold", type=float, default=1.5, help="storm Hs threshold [m]")
    p.add_argument("--peak-threshold", type=float, default=2.5, help="Hs the peak must reach [m]")
    p.add_argument("--min-duration", type=float, default=6.0, help="minimum duration [h]")
    p.add_argument("--min-separation", type=float, default=48.0,
                   help="storms closer than this form a cluster [h]")
    p.set_defaults(func=_storms)

    from .hasaki import add_cli

    add_cli(sub)
    return parser


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
