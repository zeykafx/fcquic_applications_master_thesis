#!/usr/bin/env python3

import argparse
import os
from typing import Literal
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter, LogLocator
import numpy as np
import pandas as pd
from style import (
    BASELINE_QUIC_COLOR,
    BASELINE_QUIC_LINESTYLE,
    BASELINE_QUIC_MARKER,
    BASELINE_TCP_COLOR,
    BASELINE_TCP_LINESTYLE,
    BASELINE_TCP_MARKER,
    BASELINE_TCP_NO_TLS_COLOR,
    BASELINE_TCP_NO_TLS_LINESTYLE,
    BASELINE_TCP_NO_TLS_MARKER,
    CONFIDENCE_BAND_OPACITY,
    FCQUIC_COLOR,
    FCQUIC_FEC_COLOR,
    FCQUIC_FEC_LINESTYLE,
    FCQUIC_FEC_MARKER,
    FCQUIC_LINESTYLE,
    FCQUIC_MARKER,
    LINEWIDTH,
    MARKERSIZE,
    TOKIO_QUICHE_COLOR,
    TOKIO_QUICHE_LINESTYLE,
    TOKIO_QUICHE_MARKER,
    latexify,
)


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


def plot_average_latency_vs_receivers(
    mean_or_median: Literal["median"] | Literal["mean"],
    fcquic_grouped,
    fcquic_fec_grouped,
    baseline_grouped,
    tcp_grouped,
    tcp_no_tls_grouped,
    tokio_quiche_grouped,
    clients_range_str,
    client_range,
    topo_name,
    poisson_str,
    add_data,
    out_path,
    log: bool = False,
    no_title=False,
):
    height = 7
    width = 11
    fig, ax = plt.subplots(figsize=(width, height))
    latexify(nb_subplots_line=1, fig_height=height, fig_width=width)

    ax.set_ybound(1 if log else 0)

    if log:
        ax.set_yscale("log")
        ax.yaxis.set_major_locator(LogLocator(base=10.0, numticks=15))
        ax.yaxis.set_major_formatter(ScalarFormatter())

    # FCQUIC
    if len(fcquic_grouped) > 0:
        ax.errorbar(
            fcquic_grouped["NUM_CLIENTS"],
            fcquic_grouped[mean_or_median],
            yerr=fcquic_grouped["ci"],
            label="FC-QUIC",
            color=FCQUIC_COLOR,
            linestyle=FCQUIC_LINESTYLE,
            marker=FCQUIC_MARKER,
            markersize=MARKERSIZE,
            lw=LINEWIDTH,
            capsize=4,
            capthick=LINEWIDTH,
            elinewidth=LINEWIDTH * 0.8,
        )

    # FCQUIC-FEC
    if len(fcquic_fec_grouped) > 0:
        ax.errorbar(
            fcquic_fec_grouped["NUM_CLIENTS"],
            fcquic_fec_grouped[mean_or_median],
            yerr=fcquic_fec_grouped["ci"],
            label="FC-QUIC with FEC",
            color=FCQUIC_FEC_COLOR,
            linestyle=FCQUIC_FEC_LINESTYLE,
            marker=FCQUIC_FEC_MARKER,
            markersize=MARKERSIZE,
            lw=LINEWIDTH,
            capsize=4,
            capthick=LINEWIDTH,
            elinewidth=LINEWIDTH * 0.8,
        )

    # Baseline QUIC
    if len(baseline_grouped) > 0:
        ax.errorbar(
            baseline_grouped["NUM_CLIENTS"],
            baseline_grouped[mean_or_median],
            yerr=baseline_grouped["ci"],
            label="Baseline QUIC",
            color=BASELINE_QUIC_COLOR,
            linestyle=BASELINE_QUIC_LINESTYLE,
            marker=BASELINE_QUIC_MARKER,
            markersize=MARKERSIZE,
            lw=LINEWIDTH,
            capsize=4,
            capthick=LINEWIDTH,
            elinewidth=LINEWIDTH * 0.8,
        )

    # TCP
    if len(tcp_grouped) > 0:
        ax.errorbar(
            tcp_grouped["NUM_CLIENTS"],
            tcp_grouped[mean_or_median],
            yerr=tcp_grouped["ci"],
            label="Baseline TCP (+TLS)",
            color=BASELINE_TCP_COLOR,
            linestyle=BASELINE_TCP_LINESTYLE,
            marker=BASELINE_TCP_MARKER,
            markersize=MARKERSIZE,
            lw=LINEWIDTH,
            capsize=4,
            capthick=LINEWIDTH,
            elinewidth=LINEWIDTH * 0.8,
        )

    # TCP NO TLS
    if len(tcp_no_tls_grouped) > 0:
        ax.errorbar(
            tcp_no_tls_grouped["NUM_CLIENTS"],
            tcp_no_tls_grouped[mean_or_median],
            yerr=tcp_no_tls_grouped["ci"],
            label="Baseline TCP (NO TLS)",
            color=BASELINE_TCP_NO_TLS_COLOR,
            linestyle=BASELINE_TCP_NO_TLS_LINESTYLE,
            marker=BASELINE_TCP_NO_TLS_MARKER,
            markersize=MARKERSIZE,
            lw=LINEWIDTH,
            capsize=4,
            capthick=LINEWIDTH,
            elinewidth=LINEWIDTH * 0.8,
        )

    # Tokio-quiche
    if len(tokio_quiche_grouped) > 0:
        ax.errorbar(
            tokio_quiche_grouped["NUM_CLIENTS"],
            tokio_quiche_grouped[mean_or_median],
            yerr=tokio_quiche_grouped["ci"],
            label="Tokio-quiche",
            color=TOKIO_QUICHE_COLOR,
            linestyle=TOKIO_QUICHE_LINESTYLE,
            marker=TOKIO_QUICHE_MARKER,
            markersize=MARKERSIZE,
            lw=LINEWIDTH,
            capsize=4,
            capthick=LINEWIDTH,
            elinewidth=LINEWIDTH * 0.8,
        )

    ax.set_xlabel("Number of clients")
    ax.set_ylabel(
        f"{mean_or_median.capitalize()} Latency ({"Log scale " if log else ""}ms)",
    )

    ax.grid(True, alpha=0.3)

    ax.legend(
        bbox_to_anchor=(0.0, 1.02, 1.0, 0.102),
        loc="lower left",
        ncols=2,
        mode="expand",
        borderaxespad=0.0,
    )
    if not no_title:
        ax.set_title(
            f"{mean_or_median.capitalize()} latency vs number of clients ({poisson_str}) (additional data: {add_data}B)",
        )

    fig.savefig(
        f"{out_path}/{"log_" if log else ""}{mean_or_median}_lat_{clients_range_str}_{topo_name}_{poisson_str}.svg",
        bbox_inches="tight",
    )
    plt.close(fig)


def plot_goodput_vs_sweep(data_df, out_path, topo_name, poisson_str, no_title):
    order = ["FCQUIC", "TCP", "TCP_NO_TLS", "TOKIO_QUICHE"]
    labels = {
        "FCQUIC": "FC-QUIC",
        "TCP": "Baseline TCP (+TLS)",
        "TCP_NO_TLS": "Baseline TCP (NO TLS)",
        "TOKIO_QUICHE": "Baseline Tokio-quiche",
    }
    palette = {
        "FCQUIC": FCQUIC_COLOR,
        "TCP": BASELINE_TCP_COLOR,
        "TCP_NO_TLS": BASELINE_TCP_NO_TLS_COLOR,
        "TOKIO_QUICHE": TOKIO_QUICHE_COLOR,
    }
    line_style = {
        "FCQUIC": (FCQUIC_LINESTYLE, FCQUIC_MARKER),
        "TCP": (BASELINE_TCP_LINESTYLE, BASELINE_TCP_MARKER),
        "TCP_NO_TLS": (BASELINE_TCP_NO_TLS_LINESTYLE, BASELINE_TCP_NO_TLS_MARKER),
        "TOKIO_QUICHE": (TOKIO_QUICHE_LINESTYLE, TOKIO_QUICHE_MARKER),
    }

    directions = [
        ("y_GOODPUT-DOWN-MBPS", "down", "Downstream goodput (Mbps)"),
        ("y_GOODPUT-UP-MBPS", "up", "Upstream goodput (Mbps)"),
    ]

    candidate_axes = [
        ("NUM_CLIENTS", "Number of clients"),
        ("ADDITIONAL_DATA_SIZE", "Additional data size (bytes)"),
    ]
    sweep_col = ""
    sweep_label = ""
    for col, lbl in candidate_axes:
        if col in data_df.columns and data_df[col].nunique() > 1:
            sweep_col = col
            sweep_label = lbl
            break

    for col, direction, ylabel in directions:
        if col not in data_df.columns:
            print(f"no {col} column found, skipping {direction} goodput plot")
            continue

        cols = ["CURRENT_TEST", col] + ([sweep_col] if sweep_col else [])
        df = data_df[cols].copy()
        df = df[df[col].notna()]
        df = df[df["CURRENT_TEST"].isin(order)]
        if df.empty:
            print(f"no {direction} goodput samples, skipping plot")
            continue

        sns.set_style("whitegrid")
        width = 7
        height = 6
        fig, ax = plt.subplots(figsize=(width, height))
        latexify(nb_subplots_line=1, fig_height=height, fig_width=width)

        if not sweep_col:
            grouped = df.groupby("CURRENT_TEST")[col].agg(["mean", "std"]).reset_index()
            grouped = grouped[grouped["CURRENT_TEST"].isin(order)]
            grouped["CURRENT_TEST"] = pd.Categorical(
                grouped["CURRENT_TEST"], categories=order, ordered=True
            )
            grouped = grouped.sort_values("CURRENT_TEST")
            present = list(grouped["CURRENT_TEST"])
            bars = ax.bar(
                [labels[t] for t in present],
                grouped["mean"],
                yerr=grouped["std"].fillna(0),
                color=[palette[t] for t in present],
                width=0.5,
                edgecolor="black",
                capsize=5,
            )
            ax.bar_label(
                bars,
                labels=[f"{m:.2f}" for m in grouped["mean"]],
                padding=5,
            )
            ax.set_xlabel("Implementation")
            ax.tick_params(axis="x", rotation=20)
            sweep_str = ""
        else:
            present = [t for t in order if t in df["CURRENT_TEST"].unique()]
            for t in present:
                sub = (
                    df[df["CURRENT_TEST"] == t]
                    .groupby(sweep_col)[col]
                    .mean()
                    .reset_index()
                    .sort_values(sweep_col)
                )
                if sub.empty:
                    continue
                ls, marker = line_style[t]
                ax.plot(
                    sub[sweep_col],
                    sub[col],
                    label=labels[t],
                    color=palette[t],
                    linestyle=ls,
                    marker=marker,
                    markersize=MARKERSIZE,
                    lw=LINEWIDTH,
                )
            ax.set_xlabel(sweep_label)
            ax.legend(
                bbox_to_anchor=(0.0, 1.02, 1.0, 0.102),
                loc="lower left",
                ncols=2,
                mode="expand",
                borderaxespad=0.0,
            )
            sweep_str = f"_vs_{sweep_col.lower()}"

        ax.set_ylabel(ylabel)
        ax.set_ylim(bottom=0)
        ax.grid(True, alpha=0.3)
        if not no_title:
            title_suffix = f" vs {sweep_label.lower()}" if sweep_col else ""
            ax.set_title(
                f"{direction.capitalize()} goodput{title_suffix} ({poisson_str}): {topo_name.replace('%', 'per')}",
            )

        fig.tight_layout()
        fig.savefig(
            f"{out_path}/goodput_{direction}{sweep_str}_{topo_name}_{poisson_str}.svg",
            bbox_inches="tight",
        )
        plt.close(fig)


def get_median_std_grouped_for_df(df):
    grouped = (
        df[["NUM_CLIENTS", "y_LATENCY"]]
        .groupby("NUM_CLIENTS")
        .agg(["median", "std", "count"])
    )
    grouped = grouped.droplevel(axis=1, level=0).reset_index()
    grouped["ci"] = 1.96 * grouped["std"] / np.sqrt(grouped["count"])
    grouped["ci_lower"] = grouped["median"] - grouped["ci"]
    grouped["ci_upper"] = grouped["median"] + grouped["ci"]
    return grouped


def get_mean_std_grouped_for_df(df):
    grouped = (
        df[["NUM_CLIENTS", "y_LATENCY"]]
        .groupby("NUM_CLIENTS")
        .agg(["mean", "std", "count"])
    )
    grouped = grouped.droplevel(axis=1, level=0).reset_index()
    grouped["ci"] = 1.96 * grouped["std"] / np.sqrt(grouped["count"])
    grouped["ci_lower"] = grouped["mean"] - grouped["ci"]
    grouped["ci_upper"] = grouped["mean"] + grouped["ci"]
    return grouped


def plot_cpu_vs_receivers(
    cpu_csv_path, out_path, clients_range_str, topo_name, poisson_str, no_title
):
    cpu_df = pd.read_csv(cpu_csv_path)
    if cpu_df.empty:
        print("no CPU data, skipping cpu line plot")
        return

    cpu_df["CURRENT_TEST"] = cpu_df["CURRENT_TEST"].str.replace('"', "")

    cpu_cols = [c for c in cpu_df.columns if c.startswith("y_CPU-")]
    if not cpu_cols:
        print("no CPU data, skipping cpu line plot")
        return

    if "NUM_CLIENTS" not in cpu_df.columns:
        print("no NUM_CLIENTS column in CPU data, skipping cpu line plot")
        return

    cpu_df["NUM_CLIENTS"] = cpu_df["NUM_CLIENTS"].astype(int)
    cpu_df["mean_utilization"] = cpu_df[cpu_cols].mean(axis=1)

    implementations = {
        "FCQUIC": ("FC-QUIC", FCQUIC_COLOR, FCQUIC_LINESTYLE, FCQUIC_MARKER),
        "TCP": (
            "Baseline TCP (+TLS)",
            BASELINE_TCP_COLOR,
            BASELINE_TCP_LINESTYLE,
            BASELINE_TCP_MARKER,
        ),
        "TCP_NO_TLS": (
            "Baseline TCP (NO TLS)",
            BASELINE_TCP_NO_TLS_COLOR,
            BASELINE_TCP_NO_TLS_LINESTYLE,
            BASELINE_TCP_NO_TLS_MARKER,
        ),
        "TOKIO_QUICHE": (
            "Tokio-quiche",
            TOKIO_QUICHE_COLOR,
            TOKIO_QUICHE_LINESTYLE,
            TOKIO_QUICHE_MARKER,
        ),
    }

    height = 5
    width = 11
    fig, ax = plt.subplots(figsize=(width, height))
    latexify(nb_subplots_line=1, fig_height=height, fig_width=width)

    for test_key, (label, color, linestyle, marker) in implementations.items():
        df_impl = cpu_df[cpu_df["CURRENT_TEST"] == test_key]
        if df_impl.empty:
            continue

        grouped = (
            df_impl.groupby("NUM_CLIENTS")["mean_utilization"]
            .agg(["mean", "std", "count"])
            .reset_index()
        )
        grouped["ci"] = 1.96 * grouped["std"] / np.sqrt(grouped["count"])
        grouped["ci_lower"] = grouped["mean"] - grouped["ci"]
        grouped["ci_upper"] = grouped["mean"] + grouped["ci"]

        ax.errorbar(
            grouped["NUM_CLIENTS"],
            grouped["mean"],
            yerr=grouped["ci"],
            label=label,
            color=color,
            linestyle=linestyle,
            marker=marker,
            markersize=MARKERSIZE,
            lw=LINEWIDTH,
            capsize=4,
            capthick=LINEWIDTH,
            elinewidth=LINEWIDTH * 0.8,
        )

    ax.set_xlabel("Number of clients")
    ax.set_ylabel("Mean CPU utilization (percentage)")
    ax.set_ybound(0, 100)
    ax.grid(True, alpha=0.3)
    # ax.legend(loc="upper left")
    # place legend above the graph

    if not no_title:
        ax.legend(
            bbox_to_anchor=(0.0, 1.02, 1.0, 0.102),
            loc="lower left",
            ncols=2,
            mode="expand",
            borderaxespad=0.0,
        )
        ax.set_title(
            f"Server CPU utilization vs number of clients ({poisson_str})",
        )

    fig.tight_layout()
    fig.savefig(
        f"{out_path}/cpu_vs_receivers_{clients_range_str}_{topo_name}_{poisson_str}.svg",
        bbox_inches="tight",
    )
    plt.close(fig)


def plot_cpu_load(cpu_csv_path, out_path, topo_name, poisson_str, no_title):
    cpu_df = pd.read_csv(cpu_csv_path)
    if cpu_df.empty:
        print("no CPU data, skipping cpu plot")
        return

    # clean up the messy quotes that npf adds
    cpu_df["CURRENT_TEST"] = cpu_df["CURRENT_TEST"].str.replace('"', "")

    # the cpu load is for each core is in a different col, so aggregate them
    cpu_cols = [c for c in cpu_df.columns if c.startswith("y_CPU-")]
    if not cpu_cols:
        print("no CPU date, skipping cpu plot")
        return

    # instead of using the mean computed by the npf script, we compute it here because
    # somehow the npf computed mean doesn't always match this one... (missing data??)
    cpu_df["mean_utilization"] = cpu_df[cpu_cols].mean(axis=1)

    order = ["FCQUIC", "TCP", "TCP_NO_TLS", "TOKIO_QUICHE"]
    labels = {
        "FCQUIC": "FC-QUIC",
        "TCP": "Baseline TCP (+TLS)",
        "TCP_NO_TLS": "Baseline TCP (NO TLS)",
        "TOKIO_QUICHE": "Baseline Tokio-quiche",
    }
    palette = {
        "FCQUIC": FCQUIC_COLOR,
        "TCP": BASELINE_TCP_COLOR,
        "TCP_NO_TLS": BASELINE_TCP_NO_TLS_COLOR,
        "TOKIO_QUICHE": TOKIO_QUICHE_COLOR,
    }

    grouped = (
        cpu_df[["CURRENT_TEST", "mean_utilization"]]
        .groupby("CURRENT_TEST")["mean_utilization"]
        .agg(["mean", "std"])
        .reset_index()
    )

    grouped = grouped[grouped["CURRENT_TEST"].isin(order)]
    grouped["CURRENT_TEST"] = pd.Categorical(
        grouped["CURRENT_TEST"], categories=order, ordered=True
    )
    grouped = grouped.sort_values("CURRENT_TEST")

    grouped["implementation"] = grouped["CURRENT_TEST"].map(labels)

    sns.set_style("whitegrid")
    fig, ax = plt.subplots(figsize=(8, 8))
    latexify(nb_subplots_line=1, fig_height=8, fig_width=8)

    bars = ax.bar(
        grouped["implementation"],
        grouped["mean"],
        yerr=grouped["std"],
        color=[palette[v] for v in grouped["CURRENT_TEST"]],
        width=0.5,
        edgecolor="black",
        capsize=5,
    )

    bar_labels = [
        f"{m:.2f} +- {s:.2f}" for m, s in zip(grouped["mean"], grouped["std"])
    ]
    ax.bar_label(bars, labels=bar_labels, padding=5)

    ax.set_ybound(0)
    ax.set_xlabel("Implementation")
    ax.set_ylabel("CPU utilization percentage")
    if not no_title:
        ax.set_title(
            f"Server CPU load by implementation ({poisson_str}): {topo_name.replace('%', 'per')}",
        )

    ax.tick_params(axis="x", rotation=15)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(
        f"{out_path}/cpu_load_{topo_name}_{poisson_str}.svg", bbox_inches="tight"
    )
    plt.close(fig)


def main(res_path, out_path, no_title=False):
    data_df = pd.read_csv(res_path)
    data_df["NUM_CLIENTS"] = data_df["NUM_CLIENTS"].astype(int)

    topo_name = str(data_df["TOPO_CONF_NAME"][0]).replace('"', "")
    poisson = data_df["POISSON"][0]
    is_poisson = poisson == True

    # poisson = str(data_df["POISSON"][0]).replace('"', "")
    # is_poisson = poisson == "true"

    poisson_str = "poisson" if is_poisson else "uniform"
    print(f"is poisson?: {is_poisson}")

    additional_data = data_df["ADDITIONAL_DATA_SIZE"][0]
    print(f"additional data: {additional_data}")

    # clean up the messy quotes that npf adds
    data_df["CURRENT_TEST"] = data_df["CURRENT_TEST"].str.replace('"', "")

    plot_goodput_vs_sweep(data_df, out_path, topo_name, poisson_str, no_title)

    # # remove outliers
    # # TODO: check if this is okay
    # q = data_df["y_LATENCY"].quantile(0.999)
    # print(f"Outlier threshold: {q}")
    # data_df = data_df[data_df["y_LATENCY"] < q]

    # from microseconds to milliseconds
    data_df["y_LATENCY"] = data_df["y_LATENCY"].div(1000)

    num_clients = data_df["NUM_CLIENTS"].unique()
    clients_range_str = f"{num_clients[0]}-{num_clients[-1]}"

    client_range = np.arange(num_clients[0], num_clients[-1], 1)
    print(
        f"Number of clients for this test: {num_clients} -> range: {clients_range_str}"
    )

    df_baseline = data_df[data_df["CURRENT_TEST"] == "QUIC"]
    df_fcquic = data_df[data_df["CURRENT_TEST"] == "FCQUIC"]
    df_fcquic_fec = data_df[data_df["CURRENT_TEST"] == "FCQUIC_FEC"]
    df_tcp = data_df[data_df["CURRENT_TEST"] == "TCP"]
    df_tcp_no_tls = data_df[data_df["CURRENT_TEST"] == "TCP_NO_TLS"]
    df_tokio_quiche = data_df[data_df["CURRENT_TEST"] == "TOKIO_QUICHE"]

    len_fcquic = len(df_fcquic)
    len_tcp = len(df_tcp)
    len_tcp_no_tls = len(df_tcp_no_tls)
    len_tokio_quiche = len(df_tokio_quiche)

    print(f"Baseline TCP samples: {len_tcp}")
    print(f"Baseline TCP (NO TLS) samples: {len_tcp_no_tls}")
    print(f"FC-QUIC samples: {len_fcquic}")
    print(f"Tokio-quiche samples: {len_tokio_quiche}")

    if len_fcquic < 0.5 * len_tcp:
        print(
            "-------------------------------------- FCQUIC probably bugged during the test!! --------------------------------------"
        )

    baseline_grouped = get_median_std_grouped_for_df(df_baseline)
    fcquic_grouped = get_median_std_grouped_for_df(df_fcquic)
    fcquic_fec_grouped = get_median_std_grouped_for_df(df_fcquic_fec)
    tcp_grouped = get_median_std_grouped_for_df(df_tcp)
    tcp_no_tls_grouped = get_median_std_grouped_for_df(df_tcp_no_tls)
    tokio_quiche_grouped = get_median_std_grouped_for_df(df_tokio_quiche)

    for log in [False, True]:
        plot_average_latency_vs_receivers(
            "median",
            fcquic_grouped,
            fcquic_fec_grouped,
            baseline_grouped,
            tcp_grouped,
            tcp_no_tls_grouped,
            tokio_quiche_grouped,
            clients_range_str,
            client_range,
            topo_name,
            poisson_str,
            additional_data,
            out_path,
            log,
            no_title,
        )

    mean_baseline_grouped = get_mean_std_grouped_for_df(df_baseline)
    mean_fcquic_grouped = get_mean_std_grouped_for_df(df_fcquic)
    mean_fcquic_fec_grouped = get_mean_std_grouped_for_df(df_fcquic_fec)
    mean_tcp_grouped = get_mean_std_grouped_for_df(df_tcp)
    mean_tcp_no_tls_grouped = get_mean_std_grouped_for_df(df_tcp_no_tls)
    mean_tokio_quiche_grouped = get_mean_std_grouped_for_df(df_tokio_quiche)

    for log in [False, True]:
        plot_average_latency_vs_receivers(
            "mean",
            mean_fcquic_grouped,
            mean_fcquic_fec_grouped,
            mean_baseline_grouped,
            mean_tcp_grouped,
            mean_tcp_no_tls_grouped,
            mean_tokio_quiche_grouped,
            clients_range_str,
            client_range,
            topo_name,
            poisson_str,
            additional_data,
            out_path,
            log,
            no_title,
        )

    cpu_csv_path = res_path[:-4] + "-TLOAD.csv"
    plot_cpu_load(cpu_csv_path, out_path, topo_name, poisson_str, no_title)
    plot_cpu_vs_receivers(
        cpu_csv_path, out_path, clients_range_str, topo_name, poisson_str, no_title
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser("plots")
    parser.add_argument("file_path", type=file_path)
    parser.add_argument("out_path", type=dir_path)

    parser.add_argument(
        "--no-title",
        action="store_true",
        help="don't add a title to graphs",
    )
    args = parser.parse_args()

    main(args.file_path, args.out_path, args.no_title)
