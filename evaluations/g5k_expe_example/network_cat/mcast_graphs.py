#!/usr/bin/env python3

import argparse
import os
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.lines import Line2D

from style import COLORS, LINESTYLES, LINEWIDTH, latexify

# matches "RESULT-LATENCY-<cluster> <latency_us>" (the cluster group is optional so
# that logs produced without --per-cluster-results still get plotted as a single curve)
RESULT_RE = re.compile(r"^RESULT-LATENCY(?:-(\S+))?\s+([0-9.]+)\s*$")
# run directories are named "sz<additional_data_size>_r<run_index>"
RUN_DIR_RE = re.compile(r"^sz(\d+)_r\d+$")


def file_path(path):
    if os.path.isfile(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f"{path} is not a valid file path")


def dir_path(path):
    if os.path.isdir(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f"{path} is not a valid directory")


def format_size(n_bytes):
    for unit, factor in (("GB", 1e9), ("MB", 1e6), ("KB", 1e3)):
        if n_bytes >= factor:
            return f"{n_bytes / factor:g}{unit}"
    return f"{n_bytes}B"


def parse_raw_logs(raw_root):
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
                    "cluster": (m.group(1) or "all").capitalize(),
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


def plot_combined_cdfs(
    data_df, out_path, name, sizes=(10_000, 10_000_000), no_title=False
):

    sizes = [size for size in sizes if (data_df["additional_data_size"] == size).any()]
    clusters = sorted(data_df["cluster"].unique())
    size_labels = {size: format_size(size) for size in sizes}
    # data_df["additional_data_size"] = data_df["additional_data_size"].map(size_labels)

    sns.set_style("whitegrid")
    width = 4
    height = 2.5

    latexify(nb_subplots_line=len(sizes), fig_height=height, fig_width=width)
    fig, axs = plt.subplots(
        1, len(sizes), figsize=(width * len(sizes), height), sharey=True, squeeze=False
    )
    axs = axs[0]

    for ax, size in zip(axs, sizes):
        size_df = data_df[data_df["additional_data_size"] == size]

        for i, cluster in enumerate(clusters):
            ax.ecdf(
                size_df[size_df["cluster"] == cluster]["y_LATENCY"],
                label=cluster,
                color=COLORS[i % len(COLORS)],
                linestyle=LINESTYLES[i % len(LINESTYLES)],
                lw=LINEWIDTH,
            )

            ax.set_xlabel(f"Latency (ms). Size: {size_labels[size]}")
        ax.set_ylim(0, 1)
        ax.grid(True, alpha=0.3)

    axs[0].set_ylabel("CDF")

    handles = {}
    for ax in axs:
        for handle, label in zip(*ax.get_legend_handles_labels()):
            handles[label] = handle
    legend_labels = [cluster for cluster in clusters if cluster in handles]

    fig.legend(
        [handles[label] for label in legend_labels],
        legend_labels,
        bbox_to_anchor=(0.0, 1.02, 1.0, 0.102),
        loc="upper center",
        ncols=min(len(legend_labels), 4),
        # mode="expand",
        borderaxespad=0.0,
    )
    fig.tight_layout()

    sizes_str = "_".join(format_size(size) for size in sizes)
    fig.savefig(
        f"{out_path}/cdf_{name}_{sizes_str}.svg",
        bbox_inches="tight",
    )
    plt.close()
    print(f"wrote {out_path}/cdf_{name}_{sizes_str}.svg")


def normalize_rct(dl_comp_df, by="msg_size"):
    medians = dl_comp_df.groupby(by)["duration"].transform("median")
    return dl_comp_df["duration"].div(medians)


def plot_req_comp_time_vs_run(dl_completion_path, out_path, normalize):
    dl_comp_df = pd.read_csv(dl_completion_path)
    dl_comp_df["duration"] = dl_comp_df["duration"].div(1000)

    if normalize:
        # RCT relative to the median RCT for the same message size
        dl_comp_df["duration"] = normalize_rct(dl_comp_df)

    sns.set_style("whitegrid")
    width = 7
    height = 4
    latexify(nb_subplots_line=1, fig_height=height, fig_width=width)
    fig, ax = plt.subplots(figsize=(width, height))

    msg_sizes = sorted(dl_comp_df["msg_size"].unique())
    palette = [COLORS[i % len(COLORS)] for i in range(len(msg_sizes))]

    g = sns.barplot(
        ax=ax,
        data=dl_comp_df,
        x="run_index",
        y="duration",
        hue="msg_size",
        hue_order=msg_sizes,
        palette=palette,
    )
    sns.move_legend(ax, "upper left", bbox_to_anchor=(1, 1))

    ax.grid(True, alpha=0.3)
    # ax.set_yscale("log")
    ax.set_xlabel("Run number")
    ax.set_ylabel("RCT / median RCT (ms)" if normalize else "RCT (ms)")
    plt.savefig(
        f"{out_path}/rct_vs_runs{"_normalized" if normalize else ""}.svg",
        bbox_inches="tight",
    )
    plt.close()
    print(f"wrote {out_path}/rct_vs_runs{"_normalized" if normalize else ""}.svg")


def plot_req_comp_time_variance_across_runs(dl_completion_path, out_path):
    dl_comp_df = pd.read_csv(dl_completion_path)
    dl_comp_df["duration"] = dl_comp_df["duration"].div(1000)

    run_means_df = dl_comp_df.groupby(["msg_size", "run_index"], as_index=False).agg(
        run_rct=("duration", "mean")
    )
    var_df = run_means_df.groupby("msg_size", as_index=False).agg(
        rct_variance=("run_rct", "var")
    )

    sns.set_style("whitegrid")
    width = 7
    height = 4
    latexify(nb_subplots_line=1, fig_height=height, fig_width=width)
    fig, ax = plt.subplots(figsize=(width, height))

    msg_sizes = sorted(var_df["msg_size"].unique())
    size_labels = {size: format_size(size) for size in msg_sizes}
    var_df["msg_size"] = var_df["msg_size"].map(size_labels)
    order = [size_labels[size] for size in msg_sizes]
    palette = [COLORS[i % len(COLORS)] for i in range(len(msg_sizes))]

    g = sns.barplot(
        ax=ax,
        data=var_df,
        x="msg_size",
        order=order,
        y="rct_variance",
        hue="msg_size",
        hue_order=order,
        palette=palette,
        errorbar=None,
        legend=False,
    )

    ax.grid(True, alpha=0.3)
    ax.set_yscale("log")
    ax.set_xlabel("Message size")
    ax.set_ylabel("RCT variance across runs (ms$^2$)")
    plt.savefig(
        f"{out_path}/rct_variance_across_runs.svg",
        bbox_inches="tight",
    )
    plt.close()
    print(f"wrote {out_path}/rct_variance_across_runs.svg")


def plot_boxplot_req_comp_time_vs_size(dl_completion_path, out_path):
    dl_comp_df = pd.read_csv(dl_completion_path)
    dl_comp_df["duration"] = dl_comp_df["duration"].div(1000)


    sns.set_style("whitegrid")
    width = 6
    height = 2
    latexify(nb_subplots_line=1, fig_height=height, fig_width=width)
    fig, ax = plt.subplots(figsize=(width, height))

    msg_sizes = sorted(dl_comp_df["msg_size"].unique())
    size_labels = {size: format_size(size) for size in msg_sizes}
    dl_comp_df["msg_size"] = dl_comp_df["msg_size"].map(size_labels)
    order = [size_labels[size] for size in msg_sizes]
    palette = [COLORS[i % len(COLORS)] for i in range(len(msg_sizes))]

    g = sns.boxplot(
        ax=ax,
        data=dl_comp_df,
        x="msg_size",
        order=order,
        y="duration",
        hue="msg_size",
        hue_order=order,
        palette=palette,
        legend=False,
    )

    ax.grid(True, alpha=0.4)
    # ax.set_yscale("log")
    ax.set_xlabel("Message size")
    ax.set_ylabel("RCT (ms)")
    plt.savefig(
        f"{out_path}/rct_boxplot.svg",
        bbox_inches="tight",
    )
    plt.close()
    print(f"wrote {out_path}/rct_boxplot.svg")


def plot_req_comp_time_vs_cluster(dl_completion_path, out_path, normalize):
    dl_comp_df = pd.read_csv(dl_completion_path)
    dl_comp_df["cluster"] = dl_comp_df["cluster"].str.capitalize()
    dl_comp_df["duration"] = dl_comp_df["duration"].div(1000)
    if normalize:
        # RCT relative to the median RCT for the same message size
        dl_comp_df["duration"] = normalize_rct(dl_comp_df)

    sns.set_style("whitegrid")
    width = 5
    height = 4
    fig, ax = plt.subplots(figsize=(width, height))
    latexify(nb_subplots_line=1, fig_height=height, fig_width=width)

    clusters = sorted(dl_comp_df["cluster"].unique())
    palette = [COLORS[i % len(COLORS)] for i in range(len(clusters))]

    g = sns.catplot(
        data=dl_comp_df,
        kind="bar",
        x="cluster",
        y="duration",
        hue="cluster",
        hue_order=clusters,
        palette=palette,
        legend=False,
        # log_scale=True,
        height=height,
        aspect=width / height,
    )

    # show a dot with the color in the legend
    legend_data = {
        str(cluster): Line2D([], [], marker="o", linestyle="none", color=palette[i])
        for i, cluster in enumerate(clusters)
    }
    g.add_legend(
        legend_data=legend_data,
        title="Cluster",
        label_order=[str(cluster) for cluster in clusters],
    )

    g.set_xlabels("Cluster")
    g.set_ylabels("RCT / median RCT (ms)" if normalize else "RCT (ms)")
    ax.grid(True, alpha=0.3)
    g.savefig(
        f"{out_path}/rct_vs_cluster{"_normalized" if normalize else ""}.svg",
        bbox_inches="tight",
    )
    plt.close()
    print(f"wrote {out_path}/rct_vs_cluster{"_normalized" if normalize else ""}.svg")


def plot_loss_rate_vs_cluster(losses_path, out_path):
    losses_df = pd.read_csv(losses_path)
    losses_df["cluster"] = losses_df["cluster"].str.capitalize()
    # losses_df["loss_rate"] = losses_df["lost"].div(losses_df["total_msg_packets"])
    losses_df["loss_rate"] = losses_df["loss_rate"].mul(100)

    sns.set_style("whitegrid")
    width = 7
    height = 4
    fig, ax = plt.subplots(figsize=(width, height))
    latexify(nb_subplots_line=1, fig_height=height, fig_width=width)

    msg_sizes = sorted(losses_df["msg_size"].unique())
    palette = [COLORS[i % len(COLORS)] for i in range(len(msg_sizes))]

    g = sns.barplot(
        ax=ax,
        data=losses_df,
        # kind="violin",
        x="cluster",
        y="loss_rate",
        hue="msg_size",
        hue_order=msg_sizes,
        palette=palette,
        # legend=False,
        # height=height,
        # aspect=width / height,
    )

    # show a dot with the color in the legend
    # legend_data = {
    #     str(size): Line2D([], [], marker="o", linestyle="none", color=palette[i])
    #     for i, size in enumerate(msg_sizes)
    # }
    # g.add_legend(
    #     legend_data=legend_data,
    #     title="Message size",
    #     label_order=[str(size) for size in msg_sizes],
    # )

    sns.move_legend(ax, "upper left", bbox_to_anchor=(1, 1))
    ax.set_xlabel("Cluster")
    ax.set_ylabel("Loss rate (percentage of packets received)")
    ax.grid(True, alpha=0.3)
    plt.savefig(
        f"{out_path}/losses_vs_cluster.svg",
        bbox_inches="tight",
    )
    plt.close()
    print(f"wrote {out_path}/losses_vs_cluster.svg")


def plot_loss_rate_vs_run(losses_path, out_path):
    losses_df = pd.read_csv(losses_path)
    # losses_df["loss_rate"] = losses_df["lost"].div(losses_df["total_msg_packets"])

    sns.set_style("whitegrid")
    width = 7
    height = 4
    fig, ax = plt.subplots(figsize=(width, height))
    latexify(nb_subplots_line=1, fig_height=height, fig_width=width)

    msg_sizes = sorted(losses_df["msg_size"].unique())
    palette = [COLORS[i % len(COLORS)] for i in range(len(msg_sizes))]

    g = sns.catplot(
        data=losses_df,
        kind="violin",
        x="run_index",
        y="loss_rate",
        hue="msg_size",
        hue_order=msg_sizes,
        palette=palette,
        legend=False,
        height=height,
        aspect=width / height,
    )

    # show a dot with the color in the legend
    legend_data = {
        str(size): Line2D([], [], marker="o", linestyle="none", color=palette[i])
        for i, size in enumerate(msg_sizes)
    }
    g.add_legend(
        legend_data=legend_data,
        title="Message size",
        label_order=[str(size) for size in msg_sizes],
    )

    g.set_xlabels("Run number")
    g.set_ylabels("Loss rate")
    ax.grid(True, alpha=0.3)
    g.savefig(
        f"{out_path}/losses_vs_run.svg",
        bbox_inches="tight",
    )
    plt.close()
    print(f"wrote {out_path}/losses_vs_run.svg")


def plot_lat_vs_size(data_df, out_path):
    sns.set_style("whitegrid")
    width = 6
    height = 4
    fig, ax = plt.subplots(figsize=(width, height))
    latexify(nb_subplots_line=1, fig_height=height, fig_width=width)

    clusters = sorted(data_df["cluster"].unique())
    palette = [COLORS[i % len(COLORS)] for i in range(len(clusters))]

    sns.barplot(
        ax=ax,
        data=data_df,
        # kind="bar",
        x="additional_data_size",
        y="y_LATENCY",
        hue="cluster",
        hue_order=clusters,
        palette=palette,
        # legend=False,
        # log_scale=True,
        # log=True,
        # height=height,
        # aspect=width / height,
    )
    ax.set_yscale("log")

    # show a dot with the color in the legend
    # legend_data = {
    #     str(size): Line2D([], [], marker="o", linestyle="none", color=palette[i])
    #     for i, size in enumerate(clusters)
    # }
    # g.legend(
    #     legend_data=legend_data,
    #     title="Clusters",
    #     label_order=[str(size) for size in clusters],
    # )
    sns.move_legend(ax, "upper left", bbox_to_anchor=(1, 1))
    ax.set_xlabel("Message size (bytes)")
    ax.set_ylabel("Latency (ms)")
    ax.grid(True, alpha=0.3)
    plt.savefig(
        f"{out_path}/lat_vs_size.svg",
        bbox_inches="tight",
    )
    plt.close()
    print(f"wrote {out_path}/lat_vs_size.svg")


def plot_est_rtt_vs_size_cluster(est_rtt_path, out_path):
    est_rtt_df = pd.read_csv(est_rtt_path)
    est_rtt_df["cluster"] = est_rtt_df["cluster"].str.capitalize()

    sns.set_style("whitegrid")
    width = 7
    height = 4
    fig, ax = plt.subplots(figsize=(width, height))
    latexify(nb_subplots_line=1, fig_height=height, fig_width=width)

    clusters = (
        est_rtt_df.groupby("cluster")["smoothed_rtt"]
        .median()
        .sort_values()
        .index.tolist()
    )
    palette = [COLORS[i % len(COLORS)] for i in range(len(clusters))]

    # show the message sizes with human readable units (10KB, 100KB, 1MB, ...)
    sizes = sorted(est_rtt_df["msg_size"].unique())
    size_labels = {size: format_size(size) for size in sizes}
    est_rtt_df["msg_size"] = est_rtt_df["msg_size"].map(size_labels)

    g = sns.catplot(
        data=est_rtt_df,
        kind="bar",
        x="msg_size",
        order=[size_labels[size] for size in sizes],
        y="smoothed_rtt",
        hue="cluster",
        hue_order=clusters,
        palette=palette,
        legend=False,
        # log_scale=True,
        height=height,
        aspect=width / height,
    )

    # show a dot with the color in the legend
    legend_data = {
        str(size): Line2D([], [], marker="o", linestyle="none", color=palette[i])
        for i, size in enumerate(clusters)
    }
    g.add_legend(
        legend_data=legend_data,
        title="Clusters",
        label_order=[str(size) for size in clusters],
    )

    g.set_xlabels("Message size")
    g.set_ylabels("Estimated RTT (ms)")
    ax.grid(True, alpha=0.3)
    g.savefig(
        f"{out_path}/est_rtt_vs_size_cluster.svg",
        bbox_inches="tight",
    )
    plt.close()
    print(f"wrote {out_path}/est_rtt_vs_size_cluster.svg")


def main(
    raw_path,
    out_path,
    name,
    est_rtt_path,
    dl_completion_path,
    losses_path,
    data_size=None,
    no_title=False,
):

    plot_req_comp_time_vs_run(dl_completion_path, out_path, True)
    plot_req_comp_time_vs_run(dl_completion_path, out_path, False)
    plot_req_comp_time_variance_across_runs(dl_completion_path, out_path)
    # plot_req_comp_time_vs_cluster(dl_completion_path, out_path, True)
    # plot_req_comp_time_vs_cluster(dl_completion_path, out_path, False)
    plot_boxplot_req_comp_time_vs_size(dl_completion_path, out_path)

    plot_loss_rate_vs_cluster(losses_path, out_path)
    # plot_loss_rate_vs_run(losses_path, out_path)

    plot_est_rtt_vs_size_cluster(est_rtt_path, out_path)

    data_df = parse_raw_logs(Path(raw_path))
    if data_df.empty:
        print(f"no RESULT-LATENCY lines found under {raw_path}, nothing to plot")
        return

    # from microseconds to milliseconds
    data_df["y_LATENCY"] = data_df["y_LATENCY"].div(1000)
    data_df = data_df[data_df["y_LATENCY"] != 0]

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

    # CDFs of the smallest and largest sizes (10KB and 10MB) side by side
    plot_combined_cdfs(data_df, out_path, name, no_title=no_title)

    plot_lat_vs_size(data_df, out_path)


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
    parser.add_argument("est_rtt_path", type=file_path)
    parser.add_argument("dl_completion_path", type=file_path)
    parser.add_argument("losses_path", type=file_path)

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
        args.est_rtt_path,
        args.dl_completion_path,
        args.losses_path,
        args.data_size,
        args.no_title,
    )
