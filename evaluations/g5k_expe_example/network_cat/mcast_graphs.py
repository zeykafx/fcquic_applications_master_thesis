#!/usr/bin/env python3

import argparse
import os
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.lines import Line2D

from style import COLORS, LINESTYLES, LINEWIDTH, latexify

# matches "RESULT-LATENCY-<cluster> <latency_us>" (the cluster group is optional so
# that logs produced without --per-cluster-results still get plotted as a single curve)
RESULT_RE = re.compile(r"^RESULT-LATENCY(?:-(\S+))?\s+([0-9.]+)\s*$")
# run directories are named "sz<additional_data_size>_r<run_index>"
RUN_DIR_RE = re.compile(r"^sz(\d+)_r\d+$")

# quiche opens every connection with an initial congestion window of 10 packets
# (DEFAULT_INITIAL_CONGESTION_WINDOW_PACKETS in multicast-quic/quiche/src/lib.rs), i.e.
# initial_cwnd = 10 * max_datagram_size. The experiment's binaries use a 1350 byte UDP
# payload (tokio_fcquiche::MAX_DATAGRAM_SIZE), so the initial window is 13500 bytes.
# This matches the first "congestion_window" value logged in the sqlogs.
MAX_DATAGRAM_SIZE = 1350
INITIAL_WINDOW_PACKETS = 10
INITIAL_WINDOW_BYTES = INITIAL_WINDOW_PACKETS * MAX_DATAGRAM_SIZE


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


INITIAL_WINDOW_LABEL = (
    f"initial window ({INITIAL_WINDOW_PACKETS}$\\times$MSS"
    f" = {format_size(INITIAL_WINDOW_BYTES)})"
)


def split_traces(cwnd_df, id_cols):
    """Tag each traced connection in the cwnd csv with a unique trace id.

    The merge cell writes the rows one sqlog at a time, and the qlog clock of
    each sqlog restarts near 0, so a negative time delta between two rows of
    the same group means a new trace began. When the csv carries an id column
    (run_index / client / client_ip), it is used to separate the traces.
    """
    cwnd_df = cwnd_df.copy()
    keys = ["cluster", *id_cols]
    delta = cwnd_df.groupby(keys, sort=False)["time"].diff()
    new_trace = delta.isna() | delta.lt(0)
    cwnd_df["trace"] = new_trace.astype(int).cumsum()
    return cwnd_df


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

    # width = 7
    # height = 4

    latexify(nb_subplots_line=1, fig_height=2.2, columns=1)
    fig, ax = plt.subplots()

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
        ncols=min(len(clusters), 2),
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
    # width = 4
    # height = 2.5

    latexify(nb_subplots_line=1, columns=2, fig_height=1.7)
    fig, axs = plt.subplots(1, 2, sharey=True, squeeze=False)
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
        bbox_to_anchor=(0.0, 1.0, 1, 0.1),
        loc="upper center",
        ncols=min(len(legend_labels), 4),
        # mode="expand",
        # borderaxespad=1.0,
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
    # dl_comp_df["duration"] = dl_comp_df["duration"].div(1000)

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
    ax.set_ylabel("Normalized RCT (ms)" if normalize else "RCT (ms)")
    plt.savefig(
        f"{out_path}/rct_vs_runs{"_normalized" if normalize else ""}.svg",
        bbox_inches="tight",
    )
    plt.close()
    print(f"wrote {out_path}/rct_vs_runs{"_normalized" if normalize else ""}.svg")


def plot_req_comp_time_variance_across_runs(dl_completion_path, out_path, normalize):
    dl_comp_df = pd.read_csv(dl_completion_path)
    # dl_comp_df["duration"] = dl_comp_df["duration"].div(1000)
    if normalize:
        # RCT relative to the median RCT for the same message size
        dl_comp_df["duration"] = normalize_rct(dl_comp_df)

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
    # ax.set_yscale("log")
    ax.set_xlabel("Message size")
    ax.set_ylabel(f"{"Norm. " if normalize else ""}RCT variance across runs (ms$^2$)")
    plt.savefig(
        f"{out_path}/{"norm_" if normalize else ""}rct_variance_across_runs.svg",
        bbox_inches="tight",
    )
    plt.close()
    print(
        f"wrote {out_path}/{"norm_" if normalize else ""}rct_variance_across_runs.svg"
    )


def plot_boxplot_req_comp_time_vs_size(dl_completion_path, out_path, normalize):
    dl_comp_df = pd.read_csv(dl_completion_path)
    # dl_comp_df["duration"] = dl_comp_df["duration"].div(1000)

    if normalize:
        # RCT relative to the median RCT for the same message size
        dl_comp_df["duration"] = normalize_rct(dl_comp_df)

    sns.set_style("whitegrid")
    width = 5
    height = 2
    latexify(
        nb_subplots_line=1,
        columns=1,
        fig_height=1,
    )
    fig, ax = plt.subplots()

    msg_sizes = sorted(dl_comp_df["msg_size"].unique())
    size_labels = {size: format_size(size) for size in msg_sizes}
    dl_comp_df["msg_size"] = dl_comp_df["msg_size"].map(size_labels)
    order = [size_labels[size] for size in msg_sizes]
    # palette = [COLORS[i % len(COLORS)] for i in range(len(msg_sizes))]
    palette = sns.color_palette("colorblind")

    g = sns.lineplot(
        ax=ax,
        data=dl_comp_df,
        x="msg_size",
        y="duration",
        errorbar="sd",
        # hue="msg_size",
        # hue_order=order,
        # order=order,
        palette=palette,
        # err_style="bars"
        # legend=False,
    )

    ax.grid(True, alpha=0.4)
    # ax.set_yscale("log")
    ax.set_xlabel("File size")
    ax.set_ylabel(f"{"Norm. " if normalize else ""}RCT (ms)")
    plt.savefig(
        f"{out_path}/{"norm_" if normalize else ""}rct_boxplot.svg",
        bbox_inches="tight",
    )
    plt.close()
    print(f"wrote {out_path}/{"norm_" if normalize else ""}rct_boxplot.svg")


def parse_cpu_range(cpus):
    """Parse a taskset -c style range ("0-7", "0,2,4-6") into a list of cpu ids."""
    ids = []
    for part in cpus.split(","):
        lo, _, hi = part.partition("-")
        ids.extend(range(int(lo), int(hi or lo) + 1))
    return ids


def plot_cpu_usage_vs_size(cpu_path, out_path, server_cpus="0-7"):
    cpu_df = pd.read_csv(cpu_path)
    cpu_df = cpu_df[cpu_df["cpu_id"].isin(parse_cpu_range(server_cpus))]

    # mean utilization of the server cores at each sample, then over each run
    sample_df = cpu_df.groupby(
        ["ADDITIONAL_DATA_SIZE", "run_index", "time_rel"], as_index=False
    )["utilization_percentage"].mean()
    run_df = sample_df.groupby(
        ["ADDITIONAL_DATA_SIZE", "run_index"], as_index=False
    )["utilization_percentage"].mean()

    sns.set_style("whitegrid")
    latexify(
        nb_subplots_line=1,
        columns=1,
        fig_height=1,
    )
    fig, ax = plt.subplots()

    msg_sizes = sorted(run_df["ADDITIONAL_DATA_SIZE"].unique())
    size_labels = {size: format_size(size) for size in msg_sizes}
    run_df["msg_size"] = run_df["ADDITIONAL_DATA_SIZE"].map(size_labels)

    sns.lineplot(
        ax=ax,
        data=run_df,
        x="msg_size",
        y="utilization_percentage",
        errorbar="sd",
        marker="o",
    )

    ax.grid(True, alpha=0.4)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("File size")
    ax.set_ylabel("CPU usage")
    plt.savefig(f"{out_path}/cpu_usage_vs_size.svg", bbox_inches="tight")
    plt.close()
    print(f"wrote {out_path}/cpu_usage_vs_size.svg")


def plot_req_comp_time_vs_cluster(dl_completion_path, out_path, normalize):
    dl_comp_df = pd.read_csv(dl_completion_path)
    dl_comp_df["cluster"] = dl_comp_df["cluster"].str.capitalize()
    # dl_comp_df["duration"] = dl_comp_df["duration"].div(1000)
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
    # losses_df["loss_rate"] = losses_df["loss_rate"].mul(100)

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


# group retransmissions within 50ms of each other as one loss event
LOSS_BURST_GAP_MS = 100.0


def split_bursts(times, gap_ms=LOSS_BURST_GAP_MS):
    if len(times) == 0:
        return []
    breaks = np.nonzero(np.diff(times) > gap_ms)[0] + 1
    return np.split(times, breaks)


def plot_cwnd_growth(cwnd_path, uc_retransmissions_path, dl_completion_path, out_path):
    cwnd_df = pd.read_csv(cwnd_path)
    uc_retransmissions_path_df = pd.read_csv(uc_retransmissions_path)

    rct_df = pd.read_csv(dl_completion_path)
    rct_df["duration"] = rct_df["duration"].div(1000)

    for size in sorted(cwnd_df["msg_size"].unique()):
        size_df = cwnd_df[cwnd_df["msg_size"] == size]
        retrans_df = uc_retransmissions_path_df[
            uc_retransmissions_path_df["msg_size"] == size
        ]
        # retrans_df = retrans_df[retrans_df["time"] <= 25000]
        size_rct_df = rct_df[rct_df["msg_size"] == size]

        sns.set_style("whitegrid")
        latexify(
            nb_subplots_line=1,
            columns=1,
            fig_height=1.5,
        )
        fig_width, fig_height = plt.rcParams["figure.figsize"]
        fig, ax = plt.subplots()
        # fig, (ax, ax_events) = plt.subplots(
        #     2,
        #     1,
        #     sharex=True,
        #     gridspec_kw=dict(height_ratios=[3, 1.4]),
        #     figsize=(fig_width, fig_height * 1.6),
        # )

        run_means_df = size_rct_df.groupby(
            ["msg_size", "run_index"], as_index=False
        ).agg(run_rct=("duration", "mean"))
        # rct_runs_ordered = run_means_df.groupby("msg_size")["run_rct"]

        # fastest_run = run_means_df.loc[rct_runs_ordered.idxmin()]["run_index"]
        # slowest_run = run_means_df.loc[rct_runs_ordered.idxmax()]["run_index"]
        fastest_run = run_means_df.loc[run_means_df["run_rct"].idxmin(), "run_index"]
        slowest_run = run_means_df.loc[run_means_df["run_rct"].idxmax(), "run_index"]
        print(
            f"Fastest req. comp. time run={fastest_run}, slowest rct run={slowest_run}"
        )

        # only keep the slowest and fastest run
        size_df = size_df[size_df["run_index"].isin([fastest_run, slowest_run])]
        # print(size_df)

        runs = list(dict.fromkeys([fastest_run, slowest_run]))
        palette = sns.color_palette("colorblind")
        run_colors = {run: palette[i % len(palette)] for i, run in enumerate(runs)}

        dash_patterns = ["", (4, 2)]  # "" == solid line
        run_dashes = {
            run: dash_patterns[i % len(dash_patterns)] for i, run in enumerate(runs)
        }
        run_linestyles = {run: (0, d) if d else "-" for run, d in run_dashes.items()}
        run_labels = {fastest_run: "Fastest", slowest_run: "Slowest"}

        g = sns.lineplot(
            ax=ax,
            data=size_df,
            x="time",
            y="cwnd",
            hue="run_index",
            hue_order=runs,
            palette=run_colors,
            style="run_index",
            style_order=runs,
            dashes=run_dashes,
            lw=LINEWIDTH,
            alpha=1,
            legend=False,
        )

        for run in runs:
            run_retrans = retrans_df[retrans_df["run_index"] == run].sort_values("time")
            if run_retrans.empty:
                continue
            for burst in split_bursts(run_retrans["time"].to_numpy()):
                ax.axvline(
                    np.median(burst),
                    lw=0.7,
                    color=run_colors[run],
                    zorder=5,
                    alpha=0.9,
                    linestyle=run_linestyles[run],
                )

        fig.legend(
            handles=[
                Line2D(
                    [],
                    [],
                    color=run_colors[run],
                    lw=LINEWIDTH,
                    linestyle=run_linestyles[run],
                )
                for run in runs
            ],
            labels=[f"{run_labels[run]} ({run})" for run in runs],
            loc="upper center",
            ncols=2,
            fontsize=9,
            # mode="expand",
            bbox_to_anchor=(0.1, 1.01, 1, 0.1),
        )

        # ax_events.set_yticks([])
        # ax_events.set_ylim(len(runs) - 0.5, -0.5)  # run 0 on top
        # ax_events.set_ylabel("Run")

        ax.set_ylabel("Cwnd (bytes)")
        ax.set_xlabel("Time (ms)")
        ax.grid(True, alpha=0.3)
        # ax_events.set_xlabel("Time (ms)")
        # ax_events.grid(True, axis="x", alpha=0.3)
        fig.tight_layout()
        fig.savefig(
            f"{out_path}/cwnd_growth_{size}.svg",
            bbox_inches="tight",
        )
        plt.close()
        print(f"wrote {out_path}/cwnd_growth_{size}.svg ")


def main(
    raw_path,
    out_path,
    name,
    est_rtt_path,
    dl_completion_path,
    losses_path,
    cwnd_path,
    uc_retransmissions_path,
    data_size=None,
    no_title=False,
    cpu_path=None,
    server_cpus="0-7",
):

    # plot_req_comp_time_vs_run(dl_completion_path, out_path, True)
    plot_req_comp_time_vs_run(dl_completion_path, out_path, False)

    # plot_req_comp_time_variance_across_runs(dl_completion_path, out_path, True)
    plot_req_comp_time_variance_across_runs(dl_completion_path, out_path, False)
    # plot_req_comp_time_vs_cluster(dl_completion_path, out_path, True)
    # plot_req_comp_time_vs_cluster(dl_completion_path, out_path, False)

    # plot_boxplot_req_comp_time_vs_size(dl_completion_path, out_path, True)
    plot_boxplot_req_comp_time_vs_size(dl_completion_path, out_path, False)

    plot_loss_rate_vs_cluster(losses_path, out_path)
    # plot_loss_rate_vs_run(losses_path, out_path)

    plot_est_rtt_vs_size_cluster(est_rtt_path, out_path)
    plot_cwnd_growth(cwnd_path, uc_retransmissions_path, dl_completion_path, out_path)

    if cpu_path is not None:
        plot_cpu_usage_vs_size(cpu_path, out_path, server_cpus)

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
    parser.add_argument("cwnd_path", type=file_path)
    parser.add_argument("uc_retransmissions", type=file_path)

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
    parser.add_argument(
        "--cpu-path",
        type=file_path,
        default=None,
        help="cpu load csv (e.g. ./npf-out/{test_name}_cpu.csv)",
    )
    parser.add_argument(
        "--server-cpus",
        type=str,
        default="0-7",
        help="taskset -c range the server was pinned to",
    )
    args = parser.parse_args()

    main(
        args.raw_path,
        args.out_path,
        args.name,
        args.est_rtt_path,
        args.dl_completion_path,
        args.losses_path,
        args.cwnd_path,
        args.uc_retransmissions,
        args.data_size,
        args.no_title,
        args.cpu_path,
        args.server_cpus,
    )
