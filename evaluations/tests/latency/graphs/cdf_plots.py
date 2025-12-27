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

    # groupby returns a series of tuples, each being the value of test_index, and then a dataframe containing the rows with the same test_index value
    (
        baseline,
        fcquic_fec,
        fcquic,
    ) = data_df.groupby("test_index")
    # The first test is always the FC-QUIC test, and the second is always FCQUIC with FEC, the third is the baseline

    df_fcquic = fcquic[1]
    df_fcquic_fec = fcquic_fec[1]
    df_baseline = baseline[1]
    len_fcquic = len(df_fcquic)
    len_baseline = len(df_baseline)

    global_len = min(len_fcquic, len_baseline)
    print(f"min length of the two dataframes: {global_len}")
    df_fcquic = df_fcquic[:global_len]
    df_baseline = df_baseline[:global_len]

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
    plt.ylabel("Probability of occurence", fontsize=12)
    plt.title("Cumulative distribution of latency", fontsize=14)
    plt.xlabel("Latency (ms)", fontsize=12)
    # plt.xlim(left=0)
    plt.ylim(0, 1)
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(f"cdf_{topo_name}.png", dpi=350, bbox_inches="tight")
    plt.savefig(f"cdf_{topo_name}.svg", bbox_inches="tight")


if __name__ == "__main__":
    parser = argparse.ArgumentParser("plots")
    parser.add_argument("file_path", type=file_path)
    # parser.add_argument("-n", "--name", type=str,)
    args = parser.parse_args()

    main(args.file_path)
