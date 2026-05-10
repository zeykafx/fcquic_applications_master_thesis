#!/usr/bin/env python3

import argparse
import os
from typing import Literal
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter, LogLocator
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
    log: bool = False
):
    height = 11
    width = 11
    plt.figure(figsize=(width, height))
    latexify(nb_subplots_line=1, fig_height=height, fig_width=width)

    bax = brokenaxes(hspace=0.10)
    if log:
        for ax in bax.axs:
            ax.set_yscale("log")
            ax.yaxis.set_major_locator(LogLocator(base=10.0, numticks=15)) 
            ax.yaxis.set_major_formatter(ScalarFormatter())
            ax.tick_params(axis="y", which="minor", labelsize=8)
    
    # bax = brokenaxes(ylims=((0, 0.5), (5.5, 45)), hspace=0.10)

    # FCQUIC
    if len(fcquic_grouped) > 0:
        x_fcquic = fcquic_grouped["NUM_CLIENTS"]
        bax.plot(
            x_fcquic,
            fcquic_grouped[mean_or_median],
            label="FC-QUIC",
            color=FCQUIC_COLOR,
            linestyle=FCQUIC_LINESTYLE,
            marker=FCQUIC_MARKER,
            markersize=MARKERSIZE,
            lw=LINEWIDTH,
        )
        bax.fill_between(
            x_fcquic,
            fcquic_grouped["ci_lower"],
            fcquic_grouped["ci_upper"],
            color=FCQUIC_COLOR,
            alpha=CONFIDENCE_BAND_OPACITY,
        )

    # FCQUIC-FEC
    if len(fcquic_fec_grouped) > 0:
        x_fcquic_fec = fcquic_fec_grouped["NUM_CLIENTS"]
        bax.plot(
            x_fcquic_fec,
            fcquic_fec_grouped[mean_or_median],
            label="FC-QUIC with FEC",
            color=FCQUIC_FEC_COLOR,
            linestyle=FCQUIC_FEC_LINESTYLE,
            marker=FCQUIC_FEC_MARKER,
            markersize=MARKERSIZE,
            lw=LINEWIDTH,
        )
        bax.fill_between(
            x_fcquic_fec,
            fcquic_fec_grouped["ci_lower"],
            fcquic_fec_grouped["ci_upper"],
            color=FCQUIC_FEC_COLOR,
            alpha=CONFIDENCE_BAND_OPACITY,
        )

    # Baseline QUIC
    if len(baseline_grouped) > 0:
        x_baseline = baseline_grouped["NUM_CLIENTS"]
        bax.plot(
            x_baseline,
            baseline_grouped[mean_or_median],
            label="Baseline QUIC",
            color=BASELINE_QUIC_COLOR,
            linestyle=BASELINE_QUIC_LINESTYLE,
            marker=BASELINE_QUIC_MARKER,
            markersize=MARKERSIZE,
            lw=LINEWIDTH,
        )
        bax.fill_between(
            x_baseline,
            baseline_grouped["ci_lower"],
            baseline_grouped["ci_upper"],
            color=BASELINE_QUIC_COLOR,
            alpha=CONFIDENCE_BAND_OPACITY,
        )

    # TCP
    if len(tcp_grouped) > 0:
        x_tcp = tcp_grouped["NUM_CLIENTS"]
        bax.plot(
            x_tcp,
            tcp_grouped[mean_or_median],
            label="Baseline TCP (+TLS)",
            color=BASELINE_TCP_COLOR,
            linestyle=BASELINE_TCP_LINESTYLE,
            marker=BASELINE_TCP_MARKER,
            markersize=MARKERSIZE,
            lw=LINEWIDTH,
        )
        bax.fill_between(
            x_tcp,
            tcp_grouped["ci_lower"],
            tcp_grouped["ci_upper"],
            color=BASELINE_TCP_COLOR,
            alpha=CONFIDENCE_BAND_OPACITY,
        )

    # TCP NO TLS
    if len(tcp_no_tls_grouped) > 0:
        x_tcp_no_tls = tcp_no_tls_grouped["NUM_CLIENTS"]
        bax.plot(
            x_tcp_no_tls,
            tcp_no_tls_grouped[mean_or_median],
            label="Baseline TCP (NO TLS)",
            color=BASELINE_TCP_NO_TLS_COLOR,
            linestyle=BASELINE_TCP_NO_TLS_LINESTYLE,
            marker=BASELINE_TCP_NO_TLS_MARKER,
            markersize=MARKERSIZE,
            lw=LINEWIDTH,
        )
        bax.fill_between(
            x_tcp_no_tls,
            tcp_no_tls_grouped["ci_lower"],
            tcp_no_tls_grouped["ci_upper"],
            color=BASELINE_TCP_NO_TLS_COLOR,
            alpha=CONFIDENCE_BAND_OPACITY,
        )

    # Tokio-quiche
    if len(tokio_quiche_grouped) > 0:
        x_tokio_quiche = tokio_quiche_grouped["NUM_CLIENTS"]
        bax.plot(
            x_tokio_quiche,
            tokio_quiche_grouped[mean_or_median],
            label="Tokio-quiche",
            color=TOKIO_QUICHE_COLOR,
            linestyle=TOKIO_QUICHE_LINESTYLE,
            marker=TOKIO_QUICHE_MARKER,
            markersize=MARKERSIZE,
            lw=LINEWIDTH,
        )
        bax.fill_between(
            x_tokio_quiche,
            tokio_quiche_grouped["ci_lower"],
            tokio_quiche_grouped["ci_upper"],
            color=TOKIO_QUICHE_COLOR,
            alpha=CONFIDENCE_BAND_OPACITY,
        )

    bax.set_xlabel("Number of clients", fontsize=12, labelpad=25)

    bax.set_ylabel(
        f"{mean_or_median.capitalize()} Latency ({"Log scale " if log else ""}ms)", fontsize=12, labelpad=40
    )

    bax.grid(True, alpha=0.3)
    bax.legend(loc="upper left")
    plt.title(
        f"{mean_or_median.capitalize()} latency vs number of clients ({poisson_str}) (additional data: {add_data}B)",
        fontsize=14,
    )
    # plt.savefig(
    #     f"{out_path}/avg_lat_{clients_range_str}_{topo_name}_{poisson_str}.png",
    #     dpi=350,
    #     bbox_inches="tight",
    # )
    plt.savefig(
        f"{out_path}/{"log_" if log else ""}{mean_or_median}_lat_{clients_range_str}_{topo_name}_{poisson_str}.svg",
        bbox_inches="tight",
    )


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


def plot_cpu_load(cpu_csv_path, out_path, topo_name, poisson_str):
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

    grouped["protocol"] = grouped["CURRENT_TEST"].map(labels)

    sns.set_style("whitegrid")
    fig, ax = plt.subplots(figsize=(8, 8))
    latexify(nb_subplots_line=1, fig_height=8, fig_width=8)

    bars = ax.bar(
        grouped["protocol"],
        grouped["mean"],
        yerr=grouped["std"],
        color=[palette[v] for v in grouped["CURRENT_TEST"]],
        width=0.5,
        edgecolor="black",
        capsize=5,
    )

    bar_labels = [
        f"{m:.3f} +- {s:.2f}" for m, s in zip(grouped["mean"], grouped["std"])
    ]
    ax.bar_label(bars, labels=bar_labels, padding=5, fontsize=15)

    ax.set_ybound(0)
    ax.set_xlabel("Protocol", fontsize=13)
    ax.set_ylabel("CPU utilization percentage\n(mean over observed cores)", fontsize=13)
    ax.set_title(
        f"Server CPU load by implementation ({poisson_str}): {topo_name.replace('%', 'per')}",
        fontsize=15,
    )
    ax.tick_params(axis="x", rotation=20)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(
        f"{out_path}/cpu_load_{topo_name}_{poisson_str}.svg", bbox_inches="tight"
    )
    plt.close(fig)


def main(res_path, out_path):
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

    # remove outliers
    # TODO: check if this is okay
    q = data_df["y_LATENCY"].quantile(0.99)
    print(f"Outlier threshold: {q}")
    data_df = data_df[data_df["y_LATENCY"] < q]

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
        )

    cpu_csv_path = res_path[:-4] + "-TLOAD.csv"
    plot_cpu_load(cpu_csv_path, out_path, topo_name, poisson_str)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("plots")
    parser.add_argument("file_path", type=file_path)
    parser.add_argument("out_path", type=dir_path)
    # parser.add_argument("-n", "--name", type=str,)
    args = parser.parse_args()

    main(args.file_path, args.out_path)
