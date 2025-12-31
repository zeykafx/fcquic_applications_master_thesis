#!/usr/bin/env python3

import argparse
import os
from style import (
    COLORS,
    LINESTYLES,
    LINEWIDTH,
    MARKERSIZE,
    latexify,
    CONFIDENCE_BAND_OPACITY,
    FCQUIC_COLOR,
    FCQUIC_FEC_COLOR,
    BASELINE_QUIC_COLOR,
    BASELINE_QUIC_LINESTYLE,
    FCQUIC_FEC_LINESTYLE,
    FCQUIC_LINESTYLE,
    BASELINE_TCP_COLOR,
    BASELINE_TCP_LINESTYLE,
    FCQUIC_MARKER,
    FCQUIC_FEC_MARKER,
    BASELINE_QUIC_MARKER,
    BASELINE_TCP_MARKER,
)
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


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
    fcquic_grouped,
    fcquic_fec_grouped,
    baseline_grouped,
    tcp_grouped,
    clients_range_str,
    topo_name,
    poisson_str,
    out_path,
):

    height = 8
    width = 8
    plt.figure(figsize=(width, height))
    latexify(nb_subplots_line=1, fig_height=height, fig_width=width)

    # FCQUIC
    x_fcquic = fcquic_grouped["NUM_CLIENTS"]
    plt.plot(
        x_fcquic,
        fcquic_grouped["mean"],
        label="FC-QUIC",
        color=FCQUIC_COLOR,
        linestyle=FCQUIC_LINESTYLE,
        marker=FCQUIC_MARKER,
        markersize=MARKERSIZE,
        lw=LINEWIDTH,
    )
    plt.fill_between(
        x_fcquic,
        fcquic_grouped["ci_lower"],
        fcquic_grouped["ci_upper"],
        color=FCQUIC_COLOR,
        alpha=CONFIDENCE_BAND_OPACITY,
    )

    # FCQUIC-FEC
    x_fcquic_fec = fcquic_fec_grouped["NUM_CLIENTS"]
    plt.plot(
        x_fcquic_fec,
        fcquic_fec_grouped["mean"],
        label="FC-QUIC with FEC",
        color=FCQUIC_FEC_COLOR,
        linestyle=FCQUIC_FEC_LINESTYLE,
        marker=FCQUIC_FEC_MARKER,
        markersize=MARKERSIZE,
        lw=LINEWIDTH,
    )
    plt.fill_between(
        x_fcquic_fec,
        fcquic_fec_grouped["ci_lower"],
        fcquic_fec_grouped["ci_upper"],
        color=FCQUIC_FEC_COLOR,
        alpha=CONFIDENCE_BAND_OPACITY,
    )

    # Baseline QUIC
    x_baseline = baseline_grouped["NUM_CLIENTS"]
    plt.plot(
        x_baseline,
        baseline_grouped["mean"],
        label="Baseline QUIC",
        color=BASELINE_QUIC_COLOR,
        linestyle=BASELINE_QUIC_LINESTYLE,
        marker=BASELINE_QUIC_MARKER,
        markersize=MARKERSIZE,
        lw=LINEWIDTH,
    )
    plt.fill_between(
        x_baseline,
        baseline_grouped["ci_lower"],
        baseline_grouped["ci_upper"],
        color=BASELINE_QUIC_COLOR,
        alpha=CONFIDENCE_BAND_OPACITY,
    )

    # TCP
    x_tcp = tcp_grouped["NUM_CLIENTS"]
    plt.plot(
        x_tcp,
        tcp_grouped["mean"],
        label="Baseline TCP (+TLS)",
        color=BASELINE_TCP_COLOR,
        linestyle=BASELINE_TCP_LINESTYLE,
        marker=BASELINE_TCP_MARKER,
        markersize=MARKERSIZE,
        lw=LINEWIDTH,
    )
    plt.fill_between(
        x_tcp,
        tcp_grouped["ci_lower"],
        tcp_grouped["ci_upper"],
        color=BASELINE_TCP_COLOR,
        alpha=CONFIDENCE_BAND_OPACITY,
    )

    plt.xlabel("Number of clients", fontsize=12)
    plt.ylabel("Avg Latency (µs)", fontsize=14)
    # plt.ylim(bottom=5000)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.legend()
    plt.savefig(
        f"{out_path}/avg_lat_{clients_range_str}_{topo_name}_{poisson_str}.png",
        dpi=350,
        bbox_inches="tight",
    )
    plt.savefig(
        f"{out_path}/avg_lat_{clients_range_str}_{topo_name}_{poisson_str}.svg",
        bbox_inches="tight",
    )


def plot_avg_lat(
    data_df,
    clients_range_str,
    out_path,
    topo_name,
    poisson_str,
):
    latexify(nb_subplots_line=1, fig_height=8, fig_width=6)
    plt.figure(figsize=(10, 12))
    sns.lineplot(
        x="NUM_CLIENTS",
        y="y_LATENCY",
        hue="CURRENT_TEST",
        data=data_df,
        palette="Set2",
        style="CURRENT_TEST",
        markers=True,
        markersize=12,
        dashes=True,
        alpha=1,
        hue_order=["TCP", "FCQUIC_FEC", "FCQUIC", "QUIC"],
    )
    plt.xlabel("Number of clients")
    plt.ylabel("Average Latency (µs)")
    plt.ylim(bottom=5000)
    # plt.ylim(bottom=0)
    # plt.xticks(num_clients)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    plt.savefig(
        f"{out_path}/avg_lat_{clients_range_str}_{topo_name}_{poisson_str}.png",
        dpi=350,
        bbox_inches="tight",
    )


def plot_cdfs(
    data_df,
    clients_range_str,
    out_path,
    topo_name,
    poisson_str,
):
    latexify(nb_subplots_line=1, fig_height=8, fig_width=20)
    plt.figure(figsize=(10, 20))
    grid = sns.displot(
        kind="ecdf",
        x=data_df["y_LATENCY"] / 1000,
        hue=data_df["CURRENT_TEST"],
        palette="Set2",
        col=data_df["NUM_CLIENTS"],
        hue_order=["TCP", "FCQUIC_FEC", "FCQUIC", "QUIC"],
        height=5,
        aspect=0.8,
    )

    grid.set_axis_labels("Latency (ms)", "Proportion")
    for _, ax in grid.axes_dict.items():
        ax.grid(True, alpha=0.4)
    # plt.grid(True, alpha=0.3)

    plt.tight_layout()

    plt.savefig(
        f"{out_path}/cdfs_{clients_range_str}_{topo_name}_{poisson_str}.png",
        dpi=350,
        bbox_inches="tight",
    )


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


def main(res_path, out_path):
    data_df = pd.read_csv(res_path)

    topo_name = str(data_df["TOPO_CONF_NAME"][0]).replace('"', "")
    poisson = str(data_df["POISSON"][0]).replace('"', "")
    is_poisson = poisson == "true"
    poisson_str = "poisson" if is_poisson else "uniform"
    print(f"is poisson?: {is_poisson}")

    # clean up the messy quotes that npf adds
    data_df["CURRENT_TEST"] = data_df["CURRENT_TEST"].str.replace('"', "")

    # remove outliers
    # NOTE: is this okay to do???
    q = data_df["y_LATENCY"].quantile(0.995)
    print(f"Outlier threshold: {q}")
    data_df = data_df[data_df["y_LATENCY"] < q]

    # from microseconds to milliseconds
    data_df["y_LATENCY"] = data_df["y_LATENCY"].div(1000)

    num_clients = data_df["NUM_CLIENTS"].unique()
    clients_range_str = f"{num_clients[0]}-{num_clients[-1]}"
    print(
        f"Number of clients for this test: {num_clients} -> range: {clients_range_str}"
    )

    df_baseline = data_df[data_df["CURRENT_TEST"] == "QUIC"]
    df_fcquic = data_df[data_df["CURRENT_TEST"] == "FCQUIC"]
    df_fcquic_fec = data_df[data_df["CURRENT_TEST"] == "FCQUIC_FEC"]
    df_tcp = data_df[data_df["CURRENT_TEST"] == "TCP"]

    len_fcquic = len(df_fcquic)
    len_baseline = len(df_baseline)
    len_fcquic_fec = len(df_fcquic_fec)
    len_tcp = len(df_tcp)

    print(f"Baseline QUIC samples: {len_baseline}")
    print(f"Baseline TCP samples: {len_tcp}")
    print(f"FC-QUIC samples: {len_fcquic}")
    print(f"FC-QUIC with FEC samples: {len_fcquic_fec}")

    if len_fcquic < 0.5 * len_baseline or len_fcquic_fec < 0.5 * len_baseline:
        print(
            "-------------------------------------- FCQUIC or FCQUIC_FEC probably bugged during the test!! --------------------------------------"
        )

    baseline_grouped = get_mean_std_grouped_for_df(df_baseline)
    fcquic_grouped = get_mean_std_grouped_for_df(df_fcquic)
    fcquic_fec_grouped = get_mean_std_grouped_for_df(df_fcquic_fec)
    tcp_grouped = get_mean_std_grouped_for_df(df_tcp)

    # plot_avg_lat(data_df, clients_range_str, out_path, topo_name, poisson_str)
    plot_average_latency_vs_receivers(
        fcquic_grouped,
        fcquic_fec_grouped,
        baseline_grouped,
        tcp_grouped,
        clients_range_str,
        topo_name,
        poisson_str,
        out_path,
    )

    plot_cdfs(data_df, clients_range_str, out_path, topo_name, poisson_str)

    # filter dataframes based on CURRENT_TEST, mappings:
    # QUIC: CURRENT_TEST = "QUIC"
    # FCQUIC (no FEC): CURRENT_TEST = "FCQUIC"
    # FCQUIC with FEC: CURRENT_TEST = "FCQUIC_FEC"
    # TCP: CURRENT_TEST = "TCP"
    # df_baseline = data_df[data_df["CURRENT_TEST"] == "QUIC"]
    # df_fcquic = data_df[data_df["CURRENT_TEST"] == "FCQUIC"]
    # df_fcquic_fec = data_df[data_df["CURRENT_TEST"] == "FCQUIC_FEC"]
    # df_tcp = data_df[data_df["CURRENT_TEST"] == "TCP"]

    # len_fcquic = len(df_fcquic)
    # len_baseline = len(df_baseline)
    # len_fcquic_fec = len(df_fcquic_fec)
    # len_tcp = len(df_tcp)

    # print(f"Baseline QUIC samples: {len_baseline}")
    # print(f"Baseline TCP samples: {len_tcp}")
    # print(f"FC-QUIC samples: {len_fcquic}")
    # print(f"FC-QUIC with FEC samples: {len_fcquic_fec}")

    # if len_fcquic < 0.5 * len_baseline or len_fcquic_fec < 0.5 * len_baseline:
    #     print(
    #         "---------------- FCQUIC or FCQUIC_FEC probably bugged during the test!! ----------------"
    #     )

    # global_len = min(len_fcquic, len_baseline, len_fcquic_fec, len_tcp)
    # print(f"min length of the dataframes: {global_len}")
    # # df_fcquic = df_fcquic[:global_len]
    # # df_fcquic_fec = df_fcquic_fec[:global_len]
    # # df_baseline = df_baseline[:global_len]
    # # df_tcp = df_tcp[:global_len]

    # sns.set_style("whitegrid")
    # plt.figure(figsize=(8, 6))
    # latexify(nb_subplots_line=1, fig_height=8, fig_width=6)

    # plt.ecdf(
    #     (df_fcquic["y_LATENCY"] / 1000),
    #     label="FC-QUIC",
    #     color=COLORS[1],
    #     linestyle=LINESTYLES[0],
    #     lw=LINEWIDTH,
    # )
    # plt.ecdf(
    #     (df_fcquic_fec["y_LATENCY"] / 1000),
    #     label="FC-QUIC with FEC",
    #     color=COLORS[3],
    #     linestyle=LINESTYLES[2],
    #     lw=LINEWIDTH + 0.2,
    # )
    # plt.ecdf(
    #     (df_baseline["y_LATENCY"] / 1000),
    #     label="Baseline QUIC",
    #     color=COLORS[2],
    #     linestyle=LINESTYLES[3],
    #     lw=LINEWIDTH,
    # )
    # plt.ecdf(
    #     (df_tcp["y_LATENCY"] / 1000),
    #     label="Baseline TCP (TLS)",
    #     color=COLORS[4],
    #     linestyle=LINESTYLES[4],
    #     lw=LINEWIDTH,
    # )

    # plt.ylabel("Probability of occurence", fontsize=12)
    # plt.title(f"Cumulative distribution of latency ({poisson_str})", fontsize=14)
    # plt.xlabel("Latency (ms)", fontsize=12)
    # # plt.xlim(left=0)
    # plt.ylim(0, 1)
    # plt.legend()
    # plt.grid(True, alpha=0.3)

    # plt.tight_layout()

    # plt.savefig(
    #     f"{out_path}/cdf_{topo_name}_{poisson_str}.png",
    #     dpi=350,
    #     bbox_inches="tight",
    # )
    # plt.savefig(
    #     f"{out_path}/cdf_{topo_name}_{poisson_str}.svg",
    #     bbox_inches="tight",
    # )


if __name__ == "__main__":
    parser = argparse.ArgumentParser("plots")
    parser.add_argument("file_path", type=file_path)
    parser.add_argument("out_path", type=dir_path)
    # parser.add_argument("-n", "--name", type=str,)
    args = parser.parse_args()

    main(args.file_path, args.out_path)
