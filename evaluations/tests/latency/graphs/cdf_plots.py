#!/usr/bin/env python3

import argparse
import os

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from style import COLORS, LINESTYLES, LINEWIDTH, latexify


def file_path(path):
    if os.path.isfile(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f"{path} is not a valid file path")


def main(res_path):
    data_df = pd.read_csv(res_path)

    topo_name = str(data_df["TOPO_CONF_NAME"][0]).replace('"', "")
    is_poisson = data_df["POISSON"][0] == "true"
    print(f"is poisson?: {is_poisson}")

    # clean up the messy quotes that npf adds
    data_df["CURRENT_TEST"] = data_df["CURRENT_TEST"].str.replace('"', "")
    # data_df["FEC_MODE"] = data_df["FEC_MODE"].str.replace('"', "")

    # filter dataframes based on CURRENT_TEST, mappings:
    # QUIC: CURRENT_TEST = "QUIC"
    # FCQUIC (no FEC): CURRENT_TEST = "FCQUIC"
    # FCQUIC with FEC: CURRENT_TEST = "FCQUIC_FEC"
    # TCP: CURRENT_TEST = "TCP"
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

    global_len = min(len_fcquic, len_baseline, len_fcquic_fec, len_tcp)
    print(f"min length of the dataframes: {global_len}")
    df_fcquic = df_fcquic[:global_len]
    df_fcquic_fec = df_fcquic_fec[:global_len]
    df_baseline = df_baseline[:global_len]
    df_tcp = df_baseline[:global_len]

    sns.set_style("whitegrid")
    plt.figure(figsize=(8, 6))
    latexify(nb_subplots_line=1, fig_height=8, fig_width=6)

    plt.ecdf(
        (df_fcquic["y_LATENCY"] / 1000),
        label="FC-QUIC",
        color=COLORS[1],
        linestyle=LINESTYLES[0],
        lw=LINEWIDTH,
    )
    plt.ecdf(
        (df_fcquic_fec["y_LATENCY"] / 1000),
        label="FC-QUIC with FEC",
        color=COLORS[3],
        linestyle=LINESTYLES[2],
        lw=LINEWIDTH + 0.2,
    )
    plt.ecdf(
        (df_baseline["y_LATENCY"] / 1000),
        label="Baseline QUIC",
        color=COLORS[2],
        linestyle=LINESTYLES[3],
        lw=LINEWIDTH,
    )
    plt.ecdf(
        (df_tcp["y_LATENCY"] / 1000),
        label="Baseline TCP",
        color=COLORS[4],
        linestyle=LINESTYLES[4],
        lw=LINEWIDTH,
    )
    plt.ylabel("Probability of occurence", fontsize=12)
    plt.title("Cumulative distribution of latency", fontsize=14)
    plt.xlabel("Latency (ms)", fontsize=12)
    # plt.xlim(left=0)
    plt.ylim(0, 1)
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    poisson_str = "poisson" if is_poisson else "uniform"
    plt.savefig(f"cdf_{topo_name}_{poisson_str}.png", dpi=350, bbox_inches="tight")
    plt.savefig(f"cdf_{topo_name}_{poisson_str}.svg", bbox_inches="tight")


if __name__ == "__main__":
    parser = argparse.ArgumentParser("plots")
    parser.add_argument("file_path", type=file_path)
    # parser.add_argument("-n", "--name", type=str,)
    args = parser.parse_args()

    main(args.file_path)
