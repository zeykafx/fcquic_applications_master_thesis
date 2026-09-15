#!/usr/bin/env python3

import argparse
import os
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from style import COLORS, LINESTYLES, LINEWIDTH, latexify

# matches "RESULT-LATENCY-<cluster> <latency_us>" (the cluster group is optional so
# that logs produced without --per-cluster-results still get plotted as a single curve)
RESULT_RE = re.compile(r"^RESULT-LATENCY(?:-(\S+))?\s+([0-9.]+)\s*$")
# run directories are named "sz<additional_data_size>_r<run_index>"
RUN_DIR_RE = re.compile(r"^sz(\d+)_r\d+$")


def dir_path(path):
    if os.path.isdir(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f"{path} is not a valid directory")


def parse_raw_logs(raw_root):
    """Extract the (cluster, additional data size, latency) of each RESULT line."""
    records = []

    for log_file in sorted(raw_root.rglob("client_*.stdout")):
        # the data size is encoded in the name of the run directory, e.g. "sz1000_r0"
        # (also check the raw root itself in case it points directly to a run dir)
        additional_data_size = None
        for part in [raw_root.name, *log_file.relative_to(raw_root).parts]:
            m = RUN_DIR_RE.match(part)
            if m is not None:
                additional_data_size = int(m.group(1))
                break

        for line in log_file.read_text(errors="replace").splitlines():
            m = RESULT_RE.match(line.strip())
            if m is None:
                continue

            records.append(
                {
                    "cluster": m.group(1) or "all",
                    "additional_data_size": additional_data_size,
                    "y_LATENCY": float(m.group(2)),
                }
            )

    return pd.DataFrame.from_records(
        records, columns=["cluster", "additional_data_size", "y_LATENCY"]
    )


def plot_cluster_cdfs(data_df, out_path, name, data_size=None, no_title=False):
    clusters = sorted(data_df["cluster"].unique())

    sns.set_style("whitegrid")
    width = 7
    height = 4
    # latexify must run before the figure is created: matplotlib resolves
    # "text.usetex" when each Text object is created, so texts created together
    # with the axes (labels, ticks) of a figure made before this call would keep
    # rendering without LaTeX fonts (this used to break the first figure of each
    # run, since only the previous latexify call left usetex=True in rcParams)
    latexify(nb_subplots_line=1, fig_height=height, fig_width=width)
    fig, ax = plt.subplots(figsize=(width, height))

    for i, cluster in enumerate(clusters):
        ax.ecdf(
            data_df[data_df["cluster"] == cluster]["y_LATENCY"],
            label=cluster,
            color=COLORS[i % len(COLORS)],
            linestyle=LINESTYLES[i % len(LINESTYLES)],
            lw=LINEWIDTH,
        )

    plt.xlabel("Latency (ms)")
    plt.ylabel("CDF")
    ax.set_ylim(0, 1)

    if not no_title:
        data_size_str = (
            f" (additional data: {data_size} bytes)" if data_size is not None else ""
        )
        ax.set_title(f"Latency CDF per cluster{data_size_str}")

    ax.legend(
        bbox_to_anchor=(0.0, 1.02, 1.0, 0.102),
        loc="lower left",
        ncols=min(len(clusters), 4),
        mode="expand",
        borderaxespad=0.0,
    )
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    data_size_str = f"_datasize_{data_size}" if data_size is not None else ""
    fig.savefig(
        f"{out_path}/cdf_{name}{data_size_str}.svg",
        bbox_inches="tight",
    )
    plt.close()
    print(f"wrote {out_path}/cdf_{name}{data_size_str}.svg")


def main(raw_path, out_path, name, data_size=None, no_title=False):
    data_df = parse_raw_logs(Path(raw_path))
    if data_df.empty:
        print(f"no RESULT-LATENCY lines found under {raw_path}, nothing to plot")
        return

    # from microseconds to milliseconds
    data_df["y_LATENCY"] = data_df["y_LATENCY"].div(1000)

    if data_size is not None:
        if not (data_df["additional_data_size"] == data_size).any():
            print(f"no samples for additional data size {data_size}, nothing to plot")
            return
        data_sizes = [data_size]
    else:
        data_sizes = sorted(
            int(s) for s in data_df["additional_data_size"].dropna().unique()
        )
        if not data_sizes:
            # the run directories weren't named "sz<size>_r<i>", don't split per size
            data_sizes = [None]

    for size in data_sizes:
        if size is None:
            size_df = data_df
        else:
            size_df = data_df[data_df["additional_data_size"] == size]

        print(f"additional data size {size}: {len(size_df)} samples")
        for cluster in sorted(size_df["cluster"].unique()):
            cluster_values = size_df[size_df["cluster"] == cluster]["y_LATENCY"]
            print(
                f"  {cluster}: {len(cluster_values)} samples, "
                f"median {cluster_values.median():.2f} ms"
            )

        plot_cluster_cdfs(size_df, out_path, name, size, no_title)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("mcast latency cdf plots")
    parser.add_argument(
        "raw_path",
        type=dir_path,
        help="directory containing the raw client logs (e.g. ./npf-out/raw/{test_name})",
    )
    parser.add_argument(
        "out_path",
        type=dir_path,
        help="directory the graphs are written to",
    )
    parser.add_argument(
        "name",
        type=str,
        help="test name, used in the output file names",
    )

    parser.add_argument(
        "--data-size",
        type=int,
        default=None,
        help="only plot the runs with this additional data size (in bytes)",
    )

    parser.add_argument(
        "--no-title",
        action="store_true",
        help="don't add a title to graphs",
    )
    args = parser.parse_args()

    main(
        args.raw_path,
        args.out_path,
        args.name,
        args.data_size,
        args.no_title,
    )
