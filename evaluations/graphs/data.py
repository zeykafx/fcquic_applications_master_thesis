#!/usr/bin/env python3

import argparse
import os
from typing import Literal
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from brokenaxes import brokenaxes
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


def plot_avg_lat_vs_add_size(
    mean_or_median: Literal["median"] | Literal["mean"],
    fcquic_grouped,
    fcquic_fec_grouped,
    baseline_grouped,
    tcp_grouped,
    tcp_no_tls_grouped,
    tokio_quiche_grouped,
    add_data_range_str,
    topo_name,
    poisson_str,
    out_path,
    no_title,
):
    height = 6
    width = 9
    plt.figure(figsize=(width, height))
    latexify(nb_subplots_line=1, fig_height=height, fig_width=width)

    # bax = brokenaxes(ylims=((0, 0.5), (5, 45.0)), hspace=0.1)
    bax = plt

    # FCQUIC
    if len(fcquic_grouped) > 0:
        bax.errorbar(
            fcquic_grouped["ADDITIONAL_DATA_SIZE"],
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
        bax.errorbar(
            fcquic_fec_grouped["ADDITIONAL_DATA_SIZE"],
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
        bax.errorbar(
            baseline_grouped["ADDITIONAL_DATA_SIZE"],
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
        bax.errorbar(
            tcp_grouped["ADDITIONAL_DATA_SIZE"],
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
        bax.errorbar(
            tcp_no_tls_grouped["ADDITIONAL_DATA_SIZE"],
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
        bax.errorbar(
            tokio_quiche_grouped["ADDITIONAL_DATA_SIZE"],
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

    bax.xlabel("Message size in bytes", labelpad=25)
    # bax.set_ylabel(f"{mean_or_median.capitalize()} Latency (ms)", labelpad=40)
    bax.ylabel(f"{mean_or_median.capitalize()} Latency (ms)", labelpad=40)

    bax.grid(True, alpha=0.3)
    bax.legend(
        bbox_to_anchor=(0.0, 1.02, 1.0, 0.102),
        loc="lower left",
        ncols=2,
        mode="expand",
        borderaxespad=0.0,
    )
    if not no_title:
        plt.title(
            f"{mean_or_median.capitalize()} latency vs Message size ({poisson_str})",
        )
    plt.savefig(
        f"{out_path}/{mean_or_median}_lat_{add_data_range_str}_{topo_name}_{poisson_str}.svg",
        bbox_inches="tight",
    )


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

    order = ["FCQUIC", "FCQUIC_FEC", "QUIC", "TCP", "TCP_NO_TLS", "TOKIO_QUICHE"]
    labels = {
        "FCQUIC": "FC-QUIC",
        "FCQUIC_FEC": "FC-QUIC with FEC",
        "QUIC": "Baseline QUIC",
        "TCP": "Baseline TCP (+TLS)",
        "TCP_NO_TLS": "Baseline TCP (NO TLS)",
        "TOKIO_QUICHE": "Baseline Tokio-quiche",
    }
    palette = {
        "FCQUIC": FCQUIC_COLOR,
        "FCQUIC_FEC": FCQUIC_FEC_COLOR,
        "QUIC": BASELINE_QUIC_COLOR,
        "TCP": BASELINE_TCP_COLOR,
        "TCP_NO_TLS": BASELINE_TCP_NO_TLS_COLOR,
        "TOKIO_QUICHE": TOKIO_QUICHE_COLOR,
    }
    linestyles = {
        "FCQUIC": FCQUIC_LINESTYLE,
        "FCQUIC_FEC": FCQUIC_FEC_LINESTYLE,
        "QUIC": BASELINE_QUIC_LINESTYLE,
        "TCP": BASELINE_TCP_LINESTYLE,
        "TCP_NO_TLS": BASELINE_TCP_NO_TLS_LINESTYLE,
        "TOKIO_QUICHE": TOKIO_QUICHE_LINESTYLE,
    }
    markers = {
        "FCQUIC": FCQUIC_MARKER,
        "FCQUIC_FEC": FCQUIC_FEC_MARKER,
        "QUIC": BASELINE_QUIC_MARKER,
        "TCP": BASELINE_TCP_MARKER,
        "TCP_NO_TLS": BASELINE_TCP_NO_TLS_MARKER,
        "TOKIO_QUICHE": TOKIO_QUICHE_MARKER,
    }

    grouped = (
        cpu_df[["CURRENT_TEST", "ADDITIONAL_DATA_SIZE", "mean_utilization"]]
        .groupby(["CURRENT_TEST", "ADDITIONAL_DATA_SIZE"])["mean_utilization"]
        .agg(["mean", "std", "count"])
        .reset_index()
    )
    grouped["ci"] = 1.96 * grouped["std"] / np.sqrt(grouped["count"])
    grouped["ci_lower"] = grouped["mean"] - grouped["ci"]
    grouped["ci_upper"] = grouped["mean"] + grouped["ci"]

    grouped = grouped[grouped["CURRENT_TEST"].isin(order)]

    sns.set_style("whitegrid")
    height = 5
    width = 10
    fig, ax = plt.subplots(figsize=(width, height))
    latexify(nb_subplots_line=1, fig_height=height, fig_width=width)

    for impl in order:
        sub = grouped[grouped["CURRENT_TEST"] == impl].sort_values(
            "ADDITIONAL_DATA_SIZE"
        )
        if sub.empty:
            continue
        ax.errorbar(
            sub["ADDITIONAL_DATA_SIZE"],
            sub["mean"],
            yerr=sub["ci"],
            label=labels[impl],
            color=palette[impl],
            linestyle=linestyles[impl],
            marker=markers[impl],
            markersize=MARKERSIZE,
            lw=LINEWIDTH,
            capsize=4,
            capthick=LINEWIDTH,
            elinewidth=LINEWIDTH * 0.8,
        )

    ax.set_xlabel("Message size in bytes")
    ax.set_ylabel("CPU utilization percentage")
    ax.set_ybound(0, 100)
    ax.grid(True, alpha=0.3)
    # ax.legend(loc="upper left")
    if not no_title:
        ax.legend(
            bbox_to_anchor=(0.0, 1.02, 1.0, 0.102),
            loc="lower left",
            ncols=2,
            mode="expand",
            borderaxespad=0.0,
        )
        ax.set_title(
            f"Server CPU load by implementation ({poisson_str}): {topo_name.replace('%', 'per')}",
        )
    fig.tight_layout()
    fig.savefig(
        f"{out_path}/cpu_load_{topo_name}_{poisson_str}.svg", bbox_inches="tight"
    )
    plt.close(fig)


def get_median_std_grouped_for_df(df):
    grouped = (
        df[["ADDITIONAL_DATA_SIZE", "y_LATENCY"]]
        .groupby("ADDITIONAL_DATA_SIZE")
        .agg(["median", "std", "count"])
    )
    grouped = grouped.droplevel(axis=1, level=0).reset_index()
    grouped["ci"] = 1.96 * grouped["std"] / np.sqrt(grouped["count"])
    grouped["ci_lower"] = grouped["median"] - grouped["ci"]
    grouped["ci_upper"] = grouped["median"] + grouped["ci"]
    return grouped


def get_mean_std_grouped_for_df(df):
    grouped = (
        df[["ADDITIONAL_DATA_SIZE", "y_LATENCY"]]
        .groupby("ADDITIONAL_DATA_SIZE")
        .agg(["mean", "std", "count"])
    )
    grouped = grouped.droplevel(axis=1, level=0).reset_index()
    grouped["ci"] = 1.96 * grouped["std"] / np.sqrt(grouped["count"])
    grouped["ci_lower"] = grouped["mean"] - grouped["ci"]
    grouped["ci_upper"] = grouped["mean"] + grouped["ci"]
    return grouped


def main(res_path, out_path, no_title=False):
    data_df = pd.read_csv(res_path)

    topo_name = str(data_df["TOPO_CONF_NAME"][0]).replace('"', "")
    poisson = data_df["POISSON"][0]
    is_poisson = poisson == True

    poisson_str = "poisson" if is_poisson else "uniform"
    print(f"is poisson?: {is_poisson}")

    # clean up the messy quotes that npf adds
    data_df["CURRENT_TEST"] = data_df["CURRENT_TEST"].str.replace('"', "")

    # remove outliers
    q = data_df["y_LATENCY"].quantile(0.995)
    print(f"Outlier threshold: {q}")
    data_df = data_df[data_df["y_LATENCY"] < q]

    # from microseconds to milliseconds
    data_df["y_LATENCY"] = data_df["y_LATENCY"].div(1000)

    num_clients = data_df["NUM_CLIENTS"].unique()
    clients_range_str = f"{num_clients}"
    print(f"Number of clients for this test: {num_clients}")

    add_data_sizes = data_df["ADDITIONAL_DATA_SIZE"].unique()
    add_data_range_str = f"{add_data_sizes[0]}-{add_data_sizes[-1]}"
    print(f"Additional data sizes tested: {add_data_range_str}")

    df_baseline = data_df[data_df["CURRENT_TEST"] == "QUIC"]
    df_fcquic = data_df[data_df["CURRENT_TEST"] == "FCQUIC"]
    df_fcquic_fec = data_df[data_df["CURRENT_TEST"] == "FCQUIC_FEC"]
    df_tcp = data_df[data_df["CURRENT_TEST"] == "TCP"]
    df_tcp_no_tls = data_df[data_df["CURRENT_TEST"] == "TCP_NO_TLS"]
    df_tokio_quiche = data_df[data_df["CURRENT_TEST"] == "TOKIO_QUICHE"]

    len_fcquic = len(df_fcquic)
    len_baseline = len(df_baseline)
    len_fcquic_fec = len(df_fcquic_fec)
    len_tcp = len(df_tcp)
    len_tcp_no_tls = len(df_tcp_no_tls)
    len_tokio_quiche = len(df_tokio_quiche)

    print(f"Baseline QUIC samples: {len_baseline}")
    print(f"Baseline TCP samples: {len_tcp}")
    print(f"Baseline TCP (NO TLS) samples: {len_tcp_no_tls}")
    print(f"FC-QUIC samples: {len_fcquic}")
    print(f"FC-QUIC with FEC samples: {len_fcquic_fec}")
    print(f"Tokio-quiche samples: {len_tokio_quiche}")

    if len_fcquic < 0.5 * len_baseline or len_fcquic_fec < 0.5 * len_baseline:
        print(
            "-------------------------------------- FCQUIC or FCQUIC_FEC probably bugged during the test!! --------------------------------------"
        )

    baseline_grouped = get_median_std_grouped_for_df(df_baseline)
    fcquic_grouped = get_median_std_grouped_for_df(df_fcquic)
    fcquic_fec_grouped = get_median_std_grouped_for_df(df_fcquic_fec)
    tcp_grouped = get_median_std_grouped_for_df(df_tcp)
    tcp_no_tls_grouped = get_median_std_grouped_for_df(df_tcp_no_tls)
    tokio_quiche_grouped = get_median_std_grouped_for_df(df_tokio_quiche)

    plot_avg_lat_vs_add_size(
        "median",
        fcquic_grouped,
        fcquic_fec_grouped,
        baseline_grouped,
        tcp_grouped,
        tcp_no_tls_grouped,
        tokio_quiche_grouped,
        add_data_range_str,
        topo_name,
        poisson_str,
        out_path,
        no_title,
    )

    mean_baseline_grouped = get_mean_std_grouped_for_df(df_baseline)
    mean_fcquic_grouped = get_mean_std_grouped_for_df(df_fcquic)
    mean_fcquic_fec_grouped = get_mean_std_grouped_for_df(df_fcquic_fec)
    mean_tcp_grouped = get_mean_std_grouped_for_df(df_tcp)
    mean_tcp_no_tls_grouped = get_mean_std_grouped_for_df(df_tcp_no_tls)
    mean_tokio_quiche_grouped = get_mean_std_grouped_for_df(df_tokio_quiche)

    plot_avg_lat_vs_add_size(
        "mean",
        mean_fcquic_grouped,
        mean_fcquic_fec_grouped,
        mean_baseline_grouped,
        mean_tcp_grouped,
        mean_tcp_no_tls_grouped,
        mean_tokio_quiche_grouped,
        add_data_range_str,
        topo_name,
        poisson_str,
        out_path,
        no_title,
    )

    cpu_csv_path = res_path[:-4] + "-TLOAD.csv"
    plot_cpu_load(cpu_csv_path, out_path, topo_name, poisson_str, no_title)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("plots")
    parser.add_argument("file_path", type=file_path)
    parser.add_argument("out_path", type=dir_path)
    parser.add_argument(
        "--no-title",
        action="store_true",
    )
    args = parser.parse_args()

    main(args.file_path, args.out_path, args.no_title)
