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
    FONT_SIZE,
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


def main(res_path, out_path, clip, inset=False, no_title=False):
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
            inset=inset,
            no_title=no_title,
        )

    if len(additional_data_sizes) > 1:
        plot_mean_median_vs_data_size(
            data_df, out_path, topo_name, poisson_str, bw_mbps, no_title
        )

    plot_median_latency_bar(
        data_df, out_path, topo_name, poisson_str, no_title, mean_or_median="median"
    )
    plot_median_latency_bar(
        data_df, out_path, topo_name, poisson_str, no_title, mean_or_median="mean"
    )

    plot_goodput_vs_sweep(data_df, out_path, topo_name, poisson_str, no_title)

    cpu_csv_path = res_path[:-4] + "-TLOAD.csv"
    plot_cpu_load(cpu_csv_path, out_path, topo_name, poisson_str, no_title)
    if len(additional_data_sizes) > 1:
        plot_cpu_load_vs_add_size(cpu_csv_path, out_path, topo_name, poisson_str, no_title)


def get_median_std_grouped_for_df(df):
    grouped = (
        df[["ADDITIONAL_DATA_SIZE", "y_LATENCY"]]
        .groupby("ADDITIONAL_DATA_SIZE")
        .agg(["median", "std", "count"])
    )
    grouped = grouped.droplevel(axis=1, level=0).reset_index()
    grouped["ci"] = 1.96 * grouped["std"] / np.sqrt(grouped["count"])
    grouped["ci_lower"] = (grouped["median"] - grouped["ci"]).clip(lower=0)
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


def plot_median_latency_bar(
    data_df, out_path, topo_name, poisson_str, no_title, mean_or_median="median"
):
    q = data_df["y_LATENCY"].quantile(0.999)
    data_df = data_df[data_df["y_LATENCY"] < q].copy()
    data_df["y_LATENCY"] = data_df["y_LATENCY"].div(1000)
    data_df["CURRENT_TEST"] = data_df["CURRENT_TEST"].str.replace('"', "")

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
        data_df[["CURRENT_TEST", "y_LATENCY"]]
        .groupby("CURRENT_TEST")["y_LATENCY"]
        .agg([mean_or_median, "std"])
        .reset_index()
    )

    grouped = grouped[grouped["CURRENT_TEST"].isin(order)]
    grouped["CURRENT_TEST"] = pd.Categorical(
        grouped["CURRENT_TEST"], categories=order, ordered=True
    )
    grouped = grouped.sort_values("CURRENT_TEST")
    grouped["implementation"] = grouped["CURRENT_TEST"].map(labels)

    label_cap = mean_or_median.capitalize()

    sns.set_style("whitegrid")
    width = 8
    height = 7
    fig, ax = plt.subplots(figsize=(width, height))
    latexify(nb_subplots_line=1, fig_height=height, fig_width=width)

    bars = ax.bar(
        grouped["implementation"],
        grouped[mean_or_median],
        yerr=grouped["std"],
        color=[palette[v] for v in grouped["CURRENT_TEST"]],
        width=0.5,
        edgecolor="black",
        capsize=5,
    )

    bar_labels = [
        f"{m:.3f} +- {s:.2f}" for m, s in zip(grouped[mean_or_median], grouped["std"])
    ]
    ax.bar_label(bars, labels=bar_labels, padding=5)

    ax.set_ybound(0)
    ax.set_xlabel("Implementation")
    ax.set_ylabel(f"{label_cap} latency (ms)")
    if not no_title:
        ax.set_title(
            f"{label_cap} latency by implementation ({poisson_str}): {topo_name.replace('%', 'per')}",
            fontsize=15,
        )

    ax.tick_params(axis="x", rotation=20)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(
        f"{out_path}/{mean_or_median}_latency_bar_{topo_name}_{poisson_str}.svg",
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
        ("y_GOODPUT-PAYLOAD-DOWN-MBPS", "down", "Downstream goodput (Mbps)"),
        ("y_GOODPUT-PAYLOAD-UP-MBPS", "up", "Upstream goodput (Mbps)"),
    ]

    # whichever ax has more data is used
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
        width = 8
        height = 6
        fig, ax = plt.subplots(figsize=(width, height))
        latexify(nb_subplots_line=1, fig_height=height, fig_width=width)

        if not sweep_col:
            #  if no sweep var is found then we just tested one thing
            # so we output a bar graph
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
                fontsize=FONT_SIZE,
            )

        fig.tight_layout()
        fig.savefig(
            f"{out_path}/goodput_{direction}{sweep_str}_{topo_name}_{poisson_str}.svg",
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

    grouped["implementation"] = grouped["CURRENT_TEST"].map(labels)

    sns.set_style("whitegrid")
    width = 6
    height = 7
    fig, ax = plt.subplots(figsize=(width, height))
    latexify(nb_subplots_line=1, fig_height=height, fig_width=width)

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
    ax.bar_label(bars, labels=bar_labels, padding=2)

    ax.set_ybound(0, 110)
    ax.set_xlabel(
        "Implementation",
    )
    ax.set_ylabel(
        "CPU utilization percentage",
    )
    if not no_title:
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


def plot_cpu_load_vs_add_size(cpu_csv_path, out_path, topo_name, poisson_str, no_title):
    cpu_df = pd.read_csv(cpu_csv_path)
    if cpu_df.empty:
        print("no CPU data, skipping cpu vs add size plot")
        return

    cpu_df["CURRENT_TEST"] = cpu_df["CURRENT_TEST"].str.replace('"', "")

    cpu_cols = [c for c in cpu_df.columns if c.startswith("y_CPU-")]
    if not cpu_cols:
        print("no CPU data, skipping cpu vs add size plot")
        return

    if "ADDITIONAL_DATA_SIZE" not in cpu_df.columns:
        print("no ADDITIONAL_DATA_SIZE column, skipping cpu vs add size plot")
        return

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
    grouped = grouped[grouped["CURRENT_TEST"].isin(order)]

    sns.set_style("whitegrid")
    height = 5
    width = 10
    fig, ax = plt.subplots(figsize=(width, height))
    latexify(nb_subplots_line=1, fig_height=height, fig_width=width)

    for impl in order:
        sub = grouped[grouped["CURRENT_TEST"] == impl].sort_values("ADDITIONAL_DATA_SIZE")
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

    ax.set_xlabel("Additional data size (bytes)")
    ax.set_ylabel("CPU utilization percentage")
    ax.set_ybound(0, 100)
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
            f"Server CPU load vs additional data size ({poisson_str}): {topo_name.replace('%', 'per')}",
            fontsize=FONT_SIZE,
        )
    fig.tight_layout()
    fig.savefig(
        f"{out_path}/cpu_load_vs_add_size_{topo_name}_{poisson_str}.svg",
        bbox_inches="tight",
    )
    plt.close(fig)


def plot_mean_median_vs_data_size(
    data_df, out_path, topo_name, poisson_str, bw_mbps, no_title
):
    if "ADDITIONAL_DATA_SIZE" not in data_df.columns:
        print("No ADDITIONAL_DATA_SIZE column found, skipping mean/median plot.")
        return

    # remove outliers
    q = data_df["y_LATENCY"].quantile(0.999)
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
        width = 7
        height = 6
        plt.figure(figsize=(width, height))
        latexify(nb_subplots_line=1, fig_height=height, fig_width=width)

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
        # if bw_mbps is not None:
        #     data_sizes = sorted(data_df["ADDITIONAL_DATA_SIZE"].unique())

        #     # theoretical minimum = transmission delay across all links
        #     # packet_size = ADDITIONAL_DATA_SIZE, 4 links in tiny topo
        #     # transmission delay per link = (size_bytes * 8) / (bw_mbps * 1e6) in seconds
        #     # total = 4 * transmission delay per link, to ms
        #     num_links = 4  # HACK: must change for different topologies..., not ideal but oh well
        #     theoretical_ms = [
        #         num_links * (size * 8) / (bw_mbps * 1e6) * 1000 for size in data_sizes
        #     ]
        #     plt.plot(
        #         data_sizes,
        #         theoretical_ms,
        #         label=f"Min latency ({bw_mbps} Mbps, {num_links} links)",
        #         color="black",
        #         linestyle=":",
        #         lw=LINEWIDTH,
        #         marker="x",
        #         markersize=MARKERSIZE,
        #     )

        plt.xlabel("Additional data size (bytes)")
        plt.ylabel(f"{mean_or_median.capitalize()} Latency (ms)")
        if not no_title:
            plt.title(
                f"{mean_or_median.capitalize()} latency vs additional data size ({poisson_str}): {topo_name.replace('%', 'per')}",
                fontsize=FONT_SIZE,
            )
        plt.ylim(bottom=0)

        # place legend at the top (code from https://matplotlib.org/stable/users/explain/axes/legend_guide.html#term-legend-key)
        plt.legend(
            bbox_to_anchor=(0.0, 1.02, 1.0, 0.102),
            loc="lower left",
            ncols=2,
            mode="expand",
            borderaxespad=0.0,
        )
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(
            f"{out_path}/{mean_or_median}_latency_{topo_name}_{poisson_str}.svg",
            bbox_inches="tight",
        )
        plt.close()


def _plot_ecdfs(
    ax,
    df_fcquic,
    df_fcquic_fec,
    df_baseline,
    df_tcp,
    df_tcp_no_tls,
    df_tokio_quiche,
    add_labels=True,
):
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
    data_df,
    out_path,
    clip,
    topo_name,
    poisson_str,
    is_poisson,
    data_size,
    inset=False,
    no_title=False,
):
    # remove outliers
    # NOTE: is this okay to do???
    # q = data_df["y_LATENCY"].quantile(0.999)
    # print(f"Outlier threshold: {q}")
    # data_df = data_df[data_df["y_LATENCY"] < q]

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
            "---------------- FCQUIC probably bugged during the test!! ----------------"
        )

    global_len = min(len_fcquic, len_baseline, len_tcp, len_tokio_quiche)
    print(f"min length of the dataframes: {global_len}")

    sns.set_style("whitegrid")
    width = 7
    height = 5
    fig = plt.figure(figsize=(width, height))
    latexify(nb_subplots_line=1, fig_height=height, fig_width=width)

    ax = plt.gca()
    _plot_ecdfs(
        ax,
        df_fcquic,
        df_fcquic_fec,
        df_baseline,
        df_tcp,
        df_tcp_no_tls,
        df_tokio_quiche,
        add_labels=True,
    )

    plt.ylabel("CDF")

    # Add data size to title if available
    data_size_str = f" (data size: {data_size} bytes)" if data_size is not None else ""
    if not no_title:
        plt.title(
            f"Cumulative distribution of latency ({poisson_str}): {topo_name.replace('%', 'per')}{data_size_str} {'(clipped)' if clip else ''}",
            fontsize=FONT_SIZE,
        )

    plt.xlabel("Latency (ms)")
    plt.ylim(0, 1)

    plt.legend()
    plt.grid(True, alpha=0.3)

    # zoomed in inset
    if inset:
        axins = ax.inset_axes([0.4, 0.06, 0.55, 0.5])  # type: ignore
        axins.set_facecolor("white")
        for spine in axins.spines.values():
            spine.set_edgecolor("black")
            spine.set_linewidth(1.0)

        _plot_ecdfs(
            axins,
            df_fcquic,
            df_fcquic_fec,
            df_baseline,
            df_tcp,
            df_tcp_no_tls,
            df_tokio_quiche,
            add_labels=False,
        )

        all_latencies = (
            pd.concat(
                [
                    df_fcquic["y_LATENCY"],
                    df_fcquic_fec["y_LATENCY"],
                    df_baseline["y_LATENCY"],
                    df_tcp["y_LATENCY"],
                    df_tcp_no_tls["y_LATENCY"],
                    df_tokio_quiche["y_LATENCY"],
                ]
            )
            / 1000
        )

        # choose the latencies to show by setting x_min to the start (e.g., min or quantile(0.8)...)
        # then set x_max accordingly, so if xmin was quantile(0.9), we set xmax to max and this will show the upper boddy of the cdf (here the worst 10 of the latencies)
        # if we do the opposite and set xmin to min, then we set xmax to quantile(0.5), this will show the lower body of the cdf (here the lowest 50% of the latencies).
        x_min = float(all_latencies.quantile(0.90))
        x_max = float(all_latencies.max())
        axins.set_xlim(x_min, x_max)
        axins.set_ylim(0.9)

        axins.tick_params(labelsize=8)
        axins.grid(True, alpha=0.3)

        ax.legend(
            bbox_to_anchor=(0.0, 1.02, 1.0, 0.102),
            loc="lower left",
            ncols=2,
            mode="expand",
            borderaxespad=0.0,
        )
        # ax.legend(loc="upper left", fontsize=10, framealpha=0.9)
    else:
        ax.legend(
            bbox_to_anchor=(0.0, 1.02, 1.0, 0.102),
            loc="lower left",
            ncols=2,
            mode="expand",
            borderaxespad=0.0,
        )
        # ax.legend(loc="lower right", fontsize=10, framealpha=0.9)

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
        "--no-title",
        action="store_true",
    )
    parser.add_argument(
        "--inset",
        action="store_true",
        help="add a zoomed in inset for the cdfs",
    )
    args = parser.parse_args()

    main(args.file_path, args.out_path, args.clip, args.inset, args.no_title)
