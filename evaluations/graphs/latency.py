#!/usr/bin/env python3

import argparse
import os
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
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


def main(res_path, out_path, clip, inset=False):
    data_df = pd.read_csv(res_path)

    topo_name = str(data_df["TOPO_CONF_NAME"][0]).replace('"', "")
    poisson = data_df["POISSON"][0]
    is_poisson = poisson == True
    poisson_str = "poisson" if is_poisson else "uniform"
    print(f"is poisson?: {is_poisson}")

    # get the bandwidth from the topo name, it's always near the end of the title (e.g. tiny_10mbps)
    bw_match = re.search(r"(\d+)\s*[Mm]bps", topo_name)
    bw_mbps = int(bw_match.group(1)) if bw_match else None

    # clean up the messy quotes that npf adds
    data_df["CURRENT_TEST"] = data_df["CURRENT_TEST"].str.replace('"', "")

    if "ADDITIONAL_DATA_SIZE" in data_df.columns:
        additional_data_sizes = sorted(data_df["ADDITIONAL_DATA_SIZE"].unique())
        print(f"ADDITIONAL_DATA_SIZE values: {additional_data_sizes}")
    else:
        additional_data_sizes = [None]

    for data_size in additional_data_sizes:
        if data_size is not None:
            size_filtered_df = data_df[data_df["ADDITIONAL_DATA_SIZE"] == data_size]
        else:
            size_filtered_df = data_df

        process_and_plot(
            size_filtered_df,
            out_path,
            clip,
            topo_name,
            poisson_str,
            is_poisson,
            data_size,
            inset,
        )

    plot_mean_median_vs_data_size(data_df, out_path, topo_name, poisson_str, bw_mbps)


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


def plot_mean_median_vs_data_size(data_df, out_path, topo_name, poisson_str, bw_mbps):
    if "ADDITIONAL_DATA_SIZE" not in data_df.columns:
        print("No ADDITIONAL_DATA_SIZE column found, skipping mean/median plot.")
        return

    # remove outliers
    q = data_df["y_LATENCY"].quantile(0.995)
    print(f"Outlier threshold: {q}")
    data_df = data_df[data_df["y_LATENCY"] < q].copy()

    # from microseconds to milliseconds
    data_df["y_LATENCY"] = data_df["y_LATENCY"].div(1000)

    # clean up the messy quotes that npf adds
    data_df["CURRENT_TEST"] = data_df["CURRENT_TEST"].str.replace('"', "")

    # filter dataframes based on CURRENT_TEST
    df_baseline = data_df[data_df["CURRENT_TEST"] == "QUIC"]
    df_fcquic = data_df[data_df["CURRENT_TEST"] == "FCQUIC"]
    df_fcquic_fec = data_df[data_df["CURRENT_TEST"] == "FCQUIC_FEC"]
    df_tcp = data_df[data_df["CURRENT_TEST"] == "TCP"]
    df_tcp_no_tls = data_df[data_df["CURRENT_TEST"] == "TCP_NO_TLS"]
    df_tokio_quiche = data_df[data_df["CURRENT_TEST"] == "TOKIO_QUICHE"]

    for mean_or_median in ["mean", "median"]:
        if mean_or_median == "mean":
            fcquic_grouped = get_mean_std_grouped_for_df(df_fcquic)
            fcquic_fec_grouped = get_mean_std_grouped_for_df(df_fcquic_fec)
            baseline_grouped = get_mean_std_grouped_for_df(df_baseline)
            tcp_grouped = get_mean_std_grouped_for_df(df_tcp)
            tcp_no_tls_grouped = get_mean_std_grouped_for_df(df_tcp_no_tls)
            tokio_quiche_grouped = get_mean_std_grouped_for_df(df_tokio_quiche)
        else:
            fcquic_grouped = get_median_std_grouped_for_df(df_fcquic)
            fcquic_fec_grouped = get_median_std_grouped_for_df(df_fcquic_fec)
            baseline_grouped = get_median_std_grouped_for_df(df_baseline)
            tcp_grouped = get_median_std_grouped_for_df(df_tcp)
            tcp_no_tls_grouped = get_median_std_grouped_for_df(df_tcp_no_tls)
            tokio_quiche_grouped = get_median_std_grouped_for_df(df_tokio_quiche)

        sns.set_style("whitegrid")
        plt.figure(figsize=(8, 6))
        latexify(nb_subplots_line=1, fig_height=8, fig_width=6)

        if len(fcquic_grouped) > 0:
            x = fcquic_grouped["ADDITIONAL_DATA_SIZE"]
            plt.plot(
                x,
                fcquic_grouped[mean_or_median],
                label="FC-QUIC",
                color=FCQUIC_COLOR,
                linestyle=FCQUIC_LINESTYLE,
                marker=FCQUIC_MARKER,
                markersize=MARKERSIZE,
                lw=LINEWIDTH,
            )
            plt.fill_between(
                x,
                fcquic_grouped["ci_lower"],
                fcquic_grouped["ci_upper"],
                color=FCQUIC_COLOR,
                alpha=CONFIDENCE_BAND_OPACITY,
            )

        if len(fcquic_fec_grouped) > 0:
            x = fcquic_fec_grouped["ADDITIONAL_DATA_SIZE"]
            plt.plot(
                x,
                fcquic_fec_grouped[mean_or_median],
                label="FC-QUIC with FEC",
                color=FCQUIC_FEC_COLOR,
                linestyle=FCQUIC_FEC_LINESTYLE,
                marker=FCQUIC_FEC_MARKER,
                markersize=MARKERSIZE,
                lw=LINEWIDTH,
            )
            plt.fill_between(
                x,
                fcquic_fec_grouped["ci_lower"],
                fcquic_fec_grouped["ci_upper"],
                color=FCQUIC_FEC_COLOR,
                alpha=CONFIDENCE_BAND_OPACITY,
            )

        if len(baseline_grouped) > 0:
            x = baseline_grouped["ADDITIONAL_DATA_SIZE"]
            plt.plot(
                x,
                baseline_grouped[mean_or_median],
                label="Baseline QUIC",
                color=BASELINE_QUIC_COLOR,
                linestyle=BASELINE_QUIC_LINESTYLE,
                marker=BASELINE_QUIC_MARKER,
                markersize=MARKERSIZE,
                lw=LINEWIDTH,
            )
            plt.fill_between(
                x,
                baseline_grouped["ci_lower"],
                baseline_grouped["ci_upper"],
                color=BASELINE_QUIC_COLOR,
                alpha=CONFIDENCE_BAND_OPACITY,
            )

        if len(tcp_grouped) > 0:
            x = tcp_grouped["ADDITIONAL_DATA_SIZE"]
            plt.plot(
                x,
                tcp_grouped[mean_or_median],
                label="Baseline TCP (+TLS)",
                color=BASELINE_TCP_COLOR,
                linestyle=BASELINE_TCP_LINESTYLE,
                marker=BASELINE_TCP_MARKER,
                markersize=MARKERSIZE,
                lw=LINEWIDTH,
            )
            plt.fill_between(
                x,
                tcp_grouped["ci_lower"],
                tcp_grouped["ci_upper"],
                color=BASELINE_TCP_COLOR,
                alpha=CONFIDENCE_BAND_OPACITY,
            )

        if len(tcp_no_tls_grouped) > 0:
            x = tcp_no_tls_grouped["ADDITIONAL_DATA_SIZE"]
            plt.plot(
                x,
                tcp_no_tls_grouped[mean_or_median],
                label="Baseline TCP (NO TLS)",
                color=BASELINE_TCP_NO_TLS_COLOR,
                linestyle=BASELINE_TCP_NO_TLS_LINESTYLE,
                marker=BASELINE_TCP_NO_TLS_MARKER,
                markersize=MARKERSIZE,
                lw=LINEWIDTH,
            )
            plt.fill_between(
                x,
                tcp_no_tls_grouped["ci_lower"],
                tcp_no_tls_grouped["ci_upper"],
                color=BASELINE_TCP_NO_TLS_COLOR,
                alpha=CONFIDENCE_BAND_OPACITY,
            )

        if len(tokio_quiche_grouped) > 0:
            x = tokio_quiche_grouped["ADDITIONAL_DATA_SIZE"]
            plt.plot(
                x,
                tokio_quiche_grouped[mean_or_median],
                label="Baseline Tokio-quiche",
                color=TOKIO_QUICHE_COLOR,
                linestyle=TOKIO_QUICHE_LINESTYLE,
                marker=TOKIO_QUICHE_MARKER,
                markersize=MARKERSIZE,
                lw=LINEWIDTH,
            )
            plt.fill_between(
                x,
                tokio_quiche_grouped["ci_lower"],
                tokio_quiche_grouped["ci_upper"],
                color=TOKIO_QUICHE_COLOR,
                alpha=CONFIDENCE_BAND_OPACITY,
            )
        if bw_mbps is not None:
            data_sizes = sorted(data_df["ADDITIONAL_DATA_SIZE"].unique())
            
            # theoretical minimum = transmission delay across all links
            # packet_size = ADDITIONAL_DATA_SIZE, 4 links in tiny topo
            # transmission delay per link = (size_bytes * 8) / (bw_mbps * 1e6) in seconds
            # total = 4 * transmission delay per link, to ms
            num_links = 4  # HACK: must change for different topologies..., not ideal but oh well
            theoretical_ms = [
                num_links * (size * 8) / (bw_mbps * 1e6) * 1000 for size in data_sizes
            ]
            plt.plot(
                data_sizes,
                theoretical_ms,
                label=f"Min latency ({bw_mbps} Mbps, {num_links} links)",
                color="black",
                linestyle=":",
                lw=LINEWIDTH,
                marker="x",
                markersize=MARKERSIZE,
            )

        plt.xlabel("Additional data size (bytes)", fontsize=12)
        plt.ylabel(f"{mean_or_median.capitalize()} Latency (ms)", fontsize=12)
        plt.title(
            f"{mean_or_median.capitalize()} latency vs additional data size ({poisson_str}): {topo_name.replace('%', 'per')}",
            fontsize=14,
        )
        plt.ylim(bottom=0)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(
            f"{out_path}/{mean_or_median}_latency_{topo_name}_{poisson_str}.svg",
            bbox_inches="tight",
        )
        plt.close()


def _plot_ecdfs(ax, df_fcquic, df_fcquic_fec, df_baseline, df_tcp, df_tcp_no_tls, df_tokio_quiche, add_labels=True):
    if len(df_fcquic) > 0:
        ax.ecdf(
            (df_fcquic["y_LATENCY"] / 1000),
            label="FC-QUIC" if add_labels else None,
            color=FCQUIC_COLOR,
            linestyle=FCQUIC_LINESTYLE,
            lw=LINEWIDTH,
        )
    if len(df_fcquic_fec) > 0:
        ax.ecdf(
            (df_fcquic_fec["y_LATENCY"] / 1000),
            label="FC-QUIC with FEC" if add_labels else None,
            color=FCQUIC_FEC_COLOR,
            linestyle=FCQUIC_FEC_LINESTYLE,
            lw=LINEWIDTH + 0.2,
        )
    if len(df_baseline) > 0:
        ax.ecdf(
            (df_baseline["y_LATENCY"] / 1000),
            label="Baseline QUIC" if add_labels else None,
            color=BASELINE_QUIC_COLOR,
            linestyle=BASELINE_QUIC_LINESTYLE,
            lw=LINEWIDTH,
        )
    if len(df_tcp) > 0:
        ax.ecdf(
            (df_tcp["y_LATENCY"] / 1000),
            label="Baseline TCP (+TLS)" if add_labels else None,
            color=BASELINE_TCP_COLOR,
            linestyle=BASELINE_TCP_LINESTYLE,
            lw=LINEWIDTH,
        )
    if len(df_tcp_no_tls) > 0:
        ax.ecdf(
            (df_tcp_no_tls["y_LATENCY"] / 1000),
            label="Baseline TCP (NO TLS)" if add_labels else None,
            color=BASELINE_TCP_NO_TLS_COLOR,
            linestyle=BASELINE_TCP_NO_TLS_LINESTYLE,
            lw=LINEWIDTH,
        )
    if len(df_tokio_quiche) > 0:
        ax.ecdf(
            (df_tokio_quiche["y_LATENCY"] / 1000),
            label="Baseline Tokio-quiche" if add_labels else None,
            color=TOKIO_QUICHE_COLOR,
            linestyle=TOKIO_QUICHE_LINESTYLE,
            lw=LINEWIDTH,
        )


def process_and_plot(
    data_df, out_path, clip, topo_name, poisson_str, is_poisson, data_size, inset=False
):
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
    # TOKIO_QUICHE: CURRENT_TEST = "TOKIO_QUICHE"
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

    if "run_index" in data_df.columns:
        print("Per run breakdown")
        for test_name, df_test in [
            ("QUIC", df_baseline),
            ("TCP", df_tcp),
            ("TCP_NO_TLS", df_tcp_no_tls),
            ("FCQUIC", df_fcquic),
            ("FCQUIC_FEC", df_fcquic_fec),
            ("TOKIO_QUICHE", df_tokio_quiche),
        ]:
            if len(df_test) > 0:
                print(f"{test_name}:")
                run_counts = df_test.groupby("test_index").size()
                for run_idx, count in run_counts.items():
                    print(f"  Run {run_idx}: {count} samples")

    if len_fcquic < 0.5 * len_tcp:
        print(
            "---------------- FCQUIC or FCQUIC_FEC probably bugged during the test!! ----------------"
        )

    global_len = min(
        len_fcquic, len_baseline, len_fcquic_fec, len_tcp, len_tokio_quiche
    )
    print(f"min length of the dataframes: {global_len}")

    sns.set_style("whitegrid")
    fig = plt.figure(figsize=(8, 6))
    latexify(nb_subplots_line=1, fig_height=8, fig_width=6)

    ax = plt.gca()
    _plot_ecdfs(ax, df_fcquic, df_fcquic_fec, df_baseline, df_tcp, df_tcp_no_tls, df_tokio_quiche, add_labels=True)

    plt.ylabel("Probability of occurence", fontsize=12)

    # Add data size to title if available
    data_size_str = f" (data size: {data_size} bytes)" if data_size is not None else ""
    plt.title(
        f"Cumulative distribution of latency ({poisson_str}): {topo_name.replace('%', 'per')}{data_size_str} {'(clipped)' if clip else ''}",
        fontsize=14,
    )
    plt.xlabel("Latency (ms)", fontsize=12)
    # plt.xlim(left=0)
    plt.ylim(0, 1)
    if clip:
        plt.xlim(left=21, right=26)
    plt.legend()
    plt.grid(True, alpha=0.3)

    
    # zoomed in inset
    if inset:
        axins = ax.inset_axes([0.5, 0.06, 0.46, 0.42]) # type: ignore
        axins.set_facecolor("white")
        for spine in axins.spines.values():
            spine.set_edgecolor("black")
            spine.set_linewidth(1.0)

        _plot_ecdfs(axins, df_fcquic, df_fcquic_fec, df_baseline,
                    df_tcp, df_tcp_no_tls, df_tokio_quiche, add_labels=False)

        all_latencies = pd.concat([
            df_fcquic["y_LATENCY"], df_fcquic_fec["y_LATENCY"],
            df_baseline["y_LATENCY"], df_tcp["y_LATENCY"],
            df_tcp_no_tls["y_LATENCY"], df_tokio_quiche["y_LATENCY"],
        ]) / 1000

        # choose the latencies to show by setting x_min to the start (e.g., min or quantile(0.8)...)
        # then set x_max accordingly, so if xmin was quantile(0.9), we set xmax to max and this will show the upper boddy of the cdf (here the worst 10 of the latencies)
        # if we do the opposite and set xmin to min, then we set xmax to quantile(0.5), this will show the lower body of the cdf (here the lowest 50% of the latencies)
        x_min = float(all_latencies.quantile(0.90))
        x_max = float(all_latencies.max())
        axins.set_xlim(x_min, x_max)
        axins.set_ylim(0.9)

        axins.tick_params(labelsize=8)
        axins.grid(True, alpha=0.3)

        ax.legend(loc="upper left", fontsize=10, framealpha=0.9)
    else:
        ax.legend(loc="lower right", fontsize=10, framealpha=0.9)

    fig.tight_layout()

    clip_str = "_clipped" if clip else ""
    data_size_str = f"_datasize_{data_size}" if data_size is not None else ""
    inset_str = "_inset" if inset else ""
    if clip:
        out_path = f"{out_path}/clipped"
    # plt.savefig(
    #     f"{out_path}/cdf_{topo_name}_{poisson_str}{data_size_str}{clip_str}.png",
    #     dpi=350,
    #     bbox_inches="tight",
    # )
    plt.savefig(
        f"{out_path}/cdf_{topo_name}_{poisson_str}{data_size_str}{clip_str}{inset_str}.svg",
        bbox_inches="tight",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser("plots")
    parser.add_argument("file_path", type=file_path)
    parser.add_argument("out_path", type=dir_path)
    parser.add_argument(
        "--clip",
        action="store_true",
    )
    parser.add_argument(
        "--inset",
        action="store_true",
        help="add a zoomed in inset for the cdfs",
    )
    args = parser.parse_args()

    main(args.file_path, args.out_path, args.clip, args.inset)
