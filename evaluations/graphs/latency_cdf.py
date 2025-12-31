#!/usr/bin/env python3

import argparse
import os

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from style import (
    COLORS,
    LINESTYLES,
    LINEWIDTH,
    latexify,
    FCQUIC_COLOR,
    FCQUIC_FEC_COLOR,
    BASELINE_QUIC_COLOR,
    BASELINE_QUIC_LINESTYLE,
    FCQUIC_FEC_LINESTYLE,
    FCQUIC_LINESTYLE,
    BASELINE_TCP_COLOR,
    BASELINE_TCP_LINESTYLE,
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

    if len_fcquic < 0.5 * len_baseline or len_fcquic_fec < 0.5 * len_baseline:
        print(
            "---------------- FCQUIC or FCQUIC_FEC probably bugged during the test!! ----------------"
        )

    global_len = min(len_fcquic, len_baseline, len_fcquic_fec, len_tcp)
    print(f"min length of the dataframes: {global_len}")
    # df_fcquic = df_fcquic[:global_len]
    # df_fcquic_fec = df_fcquic_fec[:global_len]
    # df_baseline = df_baseline[:global_len]
    # df_tcp = df_tcp[:global_len]

    sns.set_style("whitegrid")
    plt.figure(figsize=(8, 6))
    latexify(nb_subplots_line=1, fig_height=8, fig_width=6)

    plt.ecdf(
        (df_fcquic["y_LATENCY"] / 1000),
        label="FC-QUIC",
        color=FCQUIC_COLOR,
        linestyle=FCQUIC_LINESTYLE,
        lw=LINEWIDTH,
    )
    plt.ecdf(
        (df_fcquic_fec["y_LATENCY"] / 1000),
        label="FC-QUIC with FEC",
        color=FCQUIC_FEC_COLOR,
        linestyle=FCQUIC_FEC_LINESTYLE,
        lw=LINEWIDTH + 0.2,
    )
    plt.ecdf(
        (df_baseline["y_LATENCY"] / 1000),
        label="Baseline QUIC",
        color=BASELINE_QUIC_COLOR,
        linestyle=BASELINE_QUIC_LINESTYLE,
        lw=LINEWIDTH,
    )
    plt.ecdf(
        (df_tcp["y_LATENCY"] / 1000),
        label="Baseline TCP (+TLS)",
        color=BASELINE_TCP_COLOR,
        linestyle=BASELINE_TCP_LINESTYLE,
        lw=LINEWIDTH,
    )

    plt.ylabel("Probability of occurence", fontsize=12)
    plt.title(f"Cumulative distribution of latency ({poisson_str})", fontsize=14)
    plt.xlabel("Latency (ms)", fontsize=12)
    # plt.xlim(left=0)
    plt.ylim(0, 1)
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.tight_layout()

    plt.savefig(
        f"{out_path}/cdf_{topo_name}_{poisson_str}.png",
        dpi=350,
        bbox_inches="tight",
    )
    plt.savefig(
        f"{out_path}/cdf_{topo_name}_{poisson_str}.svg",
        bbox_inches="tight",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser("plots")
    parser.add_argument("file_path", type=file_path)
    parser.add_argument("out_path", type=dir_path)
    # parser.add_argument("-n", "--name", type=str,)
    args = parser.parse_args()

    main(args.file_path, args.out_path)
