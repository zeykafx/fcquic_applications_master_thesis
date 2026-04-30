#!/usr/bin/env python3

import argparse
import csv
import os
from pathlib import Path
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from style import (
    CONFIDENCE_BAND_OPACITY,
    FCQUIC_RELAY_COLOR,
    FCQUIC_RELAY_LINESTYLE,
    FCQUIC_RELAY_MARKER,
    NO_RELAY_COLOR,
    NO_RELAY_LINESTYLE,
    NO_RELAY_MARKER,
    APP_RELAY_COLOR,
    APP_RELAY_LINESTYLE,
    APP_RELAY_MARKER,
    LINEWIDTH,
    MARKERSIZE,
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


def main(res_path, out_path, name, inset, ack_rate_path, cpu_csv_path):

    data_df = pd.read_csv(res_path)

    # clean up the messy quotes that npf adds
    data_df["RELAY_VERSION"] = data_df["RELAY_VERSION"].str.replace('"', "")

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
            name,
            data_size,
            inset,
        )

    copy_data = data_df.copy()
    plot_mean_median_latency(copy_data, out_path, name)
    plot_mean_median_vs_data_size(data_df, out_path, name)
    plot_ack_rate_graphs(ack_rate_path, out_path, name)
    plot_cpu_load(cpu_csv_path, out_path, name)


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


def plot_ack_rate_graphs(ack_rates_path, out_path, name):

    ack_files = {
        "none": f"{ack_rates_path}none.csv",
        "RELAY": f"{ack_rates_path}RELAY.csv",
        "APP_RELAY": f"{ack_rates_path}APP_RELAY.csv",
    }

    labels = {
        "none": "No Relay",
        "RELAY": "FCQUIC Relay",
        "APP_RELAY": "Application Relay",
    }
    palette = {
        "none": NO_RELAY_COLOR,
        "RELAY": FCQUIC_RELAY_COLOR,
        "APP_RELAY": APP_RELAY_COLOR,
    }

    records = []
    for label, path in ack_files.items():
        ack_rate_df = pd.read_csv(path)
        ack_rate_df.sort_values(by="time")

        times = ack_rate_df["time"]
        total_measured_time = (
            times.iloc[-1] - times.iloc[0]
        ) / 1000  # from ms to seconds
        sum_ack_lengths = ack_rate_df["length"].sum()
        num_acks = ack_rate_df["length"].count()
        # (total len / total time) is in bits, so div by 1 million to get megabits
        rate = (sum_ack_lengths / total_measured_time) / 1e6

        records.append(
            {
                "relay_type": labels[label],
                "ack_rate_mbps": rate,
                "num_acks": num_acks,
            }
        )

    df = pd.DataFrame(records)

    sns.set_style("whitegrid")
    fig, ax = plt.subplots(figsize=(6, 7))
    latexify(nb_subplots_line=1, fig_height=6, fig_width=7)
    bars = ax.bar(
        df["relay_type"],
        df["ack_rate_mbps"],
        color=palette.values(),
        width=0.5,
        edgecolor="black",
    )

    labels = [f"{m:.3f}" for m in df["ack_rate_mbps"]]
    ax.bar_label(bars, labels=labels, padding=5, fontsize=15)

    ax.set_xlabel("Relay implementation", fontsize=15)
    ax.set_ylabel(f"ACK rate (MB/s)", fontsize=15)
    ax.set_title("ACK rate (in MB/s) by relay implementation", fontsize=15)
    ax.set_ylim(0)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(
        f"{out_path}/ack_rates_{name}.svg",
        bbox_inches="tight",
    )
    plt.close()

    fig, ax = plt.subplots(figsize=(6, 7))
    latexify(nb_subplots_line=1, fig_height=6, fig_width=7)
    bars = ax.bar(
        df["relay_type"],
        df["num_acks"],
        color=palette.values(),
        width=0.5,
        edgecolor="black",
    )

    labels = [f"{m:.3f}" for m in df["num_acks"]]
    ax.bar_label(bars, labels=labels, padding=5, fontsize=15)

    ax.set_xlabel("Relay implementation", fontsize=15)
    ax.set_ylabel(f"Number of ACK frames", fontsize=15)
    ax.set_title(
        "Number of ACK frames received by FCQUIC source with/without relays",
        fontsize=15,
    )
    ax.set_ylim(0)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(
        f"{out_path}/num_ack_{name}.svg",
        bbox_inches="tight",
    )
    plt.close()


def plot_cpu_load(cpu_csv_path, out_path, name):
    cpu_df = pd.read_csv(cpu_csv_path)
    if cpu_df.empty:
        print("no CPU data, skipping cpu plot")
        return

    # select the rows with cpu_id = -1 (they contain the mean of the cpu usage for that time step)
    cpu_df = cpu_df[cpu_df["cpu_id"] == -1]
    # cpu_df = cpu_df[cpu_df["cpu_id"] <= 1]

    # clean up the messy quotes that npf adds
    cpu_df["RELAY_VERSION"] = cpu_df["RELAY_VERSION"].str.replace('"', "")

    order = ["none", "RELAY", "APP_RELAY"]
    labels = {
        "none": "No Relay",
        "RELAY": "FCQUIC Relay",
        "APP_RELAY": "Application Relay",
    }
    palette = {
        "none": NO_RELAY_COLOR,
        "RELAY": FCQUIC_RELAY_COLOR,
        "APP_RELAY": APP_RELAY_COLOR,
    }

    # compute mean and std of utilization percentage grouped by RELAY_VERSION
    grouped = (
        cpu_df[["RELAY_VERSION", "utilization_percentage"]]
        .groupby("RELAY_VERSION")["utilization_percentage"]
        .agg(["mean", "std"])
        .reset_index()
    )

    grouped["RELAY_VERSION"] = pd.Categorical(
        grouped["RELAY_VERSION"], categories=order, ordered=True
    )
    grouped = grouped.sort_values("RELAY_VERSION")

    grouped["relay_type"] = grouped["RELAY_VERSION"].map(labels)

    sns.set_style("whitegrid")
    fig, ax = plt.subplots(figsize=(8, 8))
    latexify(nb_subplots_line=1, fig_height=8, fig_width=8)
    bars = ax.bar(
        grouped["relay_type"],
        grouped["mean"],
        yerr=grouped["std"],
        color=palette.values(),
        width=0.5,
        edgecolor="black",
        capsize=5,
    )

    labels = [f"{m:.3f} +- {s:.2f}" for m, s in zip(grouped["mean"], grouped["std"])]
    ax.bar_label(bars, labels=labels, padding=5, fontsize=15)

    ax.set_xlabel("Relay implementation", fontsize=13)
    ax.set_ylabel("CPU utilization percentage\n(mean over observed cores)", fontsize=13)
    ax.set_title(
        "FCQUIC Source CPU Load with different relay implementations", fontsize=15
    )
    # ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(f"{out_path}/cpu_load_{name}.svg", bbox_inches="tight")
    plt.close(fig)


def plot_mean_median_latency(data_df, out_path, name):
    # q = data_df["y_LATENCY"].quantile(0.995)
    # print(f"Outlier threshold: {q}")
    # data_df = data_df[data_df["y_LATENCY"] < q].copy()

    # from microseconds to milliseconds
    data_df["y_LATENCY"] = data_df["y_LATENCY"].div(1000)

    # clean up the messy quotes that npf adds
    data_df["RELAY_VERSION"] = data_df["RELAY_VERSION"].str.replace('"', "")

    order = ["none", "RELAY", "APP_RELAY"]
    labels = {
        "none": "No Relay",
        "RELAY": "FCQUIC Relay",
        "APP_RELAY": "Application Relay",
    }
    palette = {
        "none": NO_RELAY_COLOR,
        "RELAY": FCQUIC_RELAY_COLOR,
        "APP_RELAY": APP_RELAY_COLOR,
    }

    for mean_or_median in ["mean", "median"]:
        if mean_or_median == "mean":
            grouped = (
                data_df[["RELAY_VERSION", "y_LATENCY"]]
                .groupby("RELAY_VERSION")["y_LATENCY"]
                .agg(["mean", "std"])
                .reset_index()
            )
        else:
            grouped = (
                data_df[["RELAY_VERSION", "y_LATENCY"]]
                .groupby("RELAY_VERSION")["y_LATENCY"]
                .agg(["median", "std"])
                .reset_index()
            )

        grouped = grouped[grouped["RELAY_VERSION"].isin(order)]

        grouped["RELAY_VERSION"] = pd.Categorical(
            grouped["RELAY_VERSION"], categories=order, ordered=True
        )
        grouped = grouped.sort_values("RELAY_VERSION")
        grouped["relay_type"] = grouped["RELAY_VERSION"].map(labels)

        sns.set_style("whitegrid")
        fig, ax = plt.subplots(figsize=(8, 6))
        latexify(nb_subplots_line=1, fig_height=8, fig_width=6)

        bars = ax.bar(
            grouped["relay_type"],
            grouped[mean_or_median],
            yerr=grouped["std"],
            width=0.5,
            edgecolor="black",
            capsize=5,
            color=[palette[v] for v in grouped["RELAY_VERSION"]],
        )

        labels_axes = [
            f"{m:.3f} +- {s:.2f}"
            for m, s in zip(grouped[mean_or_median], grouped["std"])
        ]
        ax.bar_label(bars, labels=labels_axes, padding=5, fontsize=15)

        ax.set_xlabel("Relay implementation", fontsize=13)
        ax.set_ylabel(f"{mean_or_median.capitalize()} Latency (ms)", fontsize=13)
        ax.set_title(
            f"{mean_or_median.capitalize()} latency vs Relay Implementation",
            fontsize=15,
        )
        ax.set_ylim(0)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(
            f"{out_path}/{mean_or_median}_latency_vs_relay_{name}.svg",
            bbox_inches="tight",
        )
        plt.close(fig)


def plot_mean_median_vs_data_size(data_df, out_path, name):
    if "ADDITIONAL_DATA_SIZE" not in data_df.columns:
        print("No ADDITIONAL_DATA_SIZE column found, skipping mean/median plot.")
        return

    if data_df["ADDITIONAL_DATA_SIZE"].nunique() <= 1:
        print("only one additional data size, skipping mean/median plot.")
        return

    # # remove outliers
    # q = data_df["y_LATENCY"].quantile(0.995)
    # print(f"Outlier threshold: {q}")
    # data_df = data_df[data_df["y_LATENCY"] < q].copy()

    # from microseconds to milliseconds
    data_df["y_LATENCY"] = data_df["y_LATENCY"].div(1000)

    # clean up the messy quotes that npf adds
    data_df["RELAY_VERSION"] = data_df["RELAY_VERSION"].str.replace('"', "")

    # filter dataframes based on RELAY_VERSION, mappings:
    df_no_relay = data_df[data_df["RELAY_VERSION"] == "none"]
    df_fcquic_relay = data_df[data_df["RELAY_VERSION"] == "RELAY"]
    df_app_relay = data_df[data_df["RELAY_VERSION"] == "APP_RELAY"]

    for mean_or_median in ["mean", "median"]:
        if mean_or_median == "mean":
            no_relay_grouped = get_mean_std_grouped_for_df(df_no_relay)
            fcquic_relay_grouped = get_mean_std_grouped_for_df(df_fcquic_relay)
            app_relay_grouped = get_mean_std_grouped_for_df(df_app_relay)
        else:
            no_relay_grouped = get_median_std_grouped_for_df(df_no_relay)
            fcquic_relay_grouped = get_median_std_grouped_for_df(df_fcquic_relay)
            app_relay_grouped = get_median_std_grouped_for_df(df_app_relay)

        sns.set_style("whitegrid")
        plt.figure(figsize=(8, 6))
        latexify(nb_subplots_line=1, fig_height=8, fig_width=6)

        if len(no_relay_grouped) > 0:
            x = no_relay_grouped["ADDITIONAL_DATA_SIZE"]
            plt.plot(
                x,
                no_relay_grouped[mean_or_median],
                label="No Relay",
                color=NO_RELAY_COLOR,
                linestyle=NO_RELAY_LINESTYLE,
                marker=NO_RELAY_MARKER,
                markersize=MARKERSIZE,
                lw=LINEWIDTH,
            )
            plt.fill_between(
                x,
                no_relay_grouped["ci_lower"],
                no_relay_grouped["ci_upper"],
                color=NO_RELAY_COLOR,
                alpha=CONFIDENCE_BAND_OPACITY,
            )

        if len(fcquic_relay_grouped) > 0:
            x = fcquic_relay_grouped["ADDITIONAL_DATA_SIZE"]
            plt.plot(
                x,
                fcquic_relay_grouped[mean_or_median],
                label="FCQUIC Relay",
                color=FCQUIC_RELAY_COLOR,
                linestyle=FCQUIC_RELAY_LINESTYLE,
                marker=FCQUIC_RELAY_MARKER,
                markersize=MARKERSIZE,
                lw=LINEWIDTH,
            )
            plt.fill_between(
                x,
                fcquic_relay_grouped["ci_lower"],
                fcquic_relay_grouped["ci_upper"],
                color=FCQUIC_RELAY_COLOR,
                alpha=CONFIDENCE_BAND_OPACITY,
            )

        if len(app_relay_grouped) > 0:
            x = app_relay_grouped["ADDITIONAL_DATA_SIZE"]
            plt.plot(
                x,
                app_relay_grouped[mean_or_median],
                label="Application relay",
                color=APP_RELAY_COLOR,
                linestyle=APP_RELAY_LINESTYLE,
                marker=APP_RELAY_MARKER,
                markersize=MARKERSIZE,
                lw=LINEWIDTH,
            )
            plt.fill_between(
                x,
                app_relay_grouped["ci_lower"],
                app_relay_grouped["ci_upper"],
                color=APP_RELAY_COLOR,
                alpha=CONFIDENCE_BAND_OPACITY,
            )

        plt.xlabel("Additional data size (bytes)", fontsize=13)
        plt.ylabel(f"{mean_or_median.capitalize()} Latency (ms)", fontsize=13)
        plt.title(
            f"{mean_or_median.capitalize()} latency vs additional data size",
            fontsize=15,
        )
        # plt.ylim(bottom=0)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(
            f"{out_path}/{mean_or_median}_latency_{name}.svg",
            bbox_inches="tight",
        )
        plt.close()


def _plot_ecdfs(ax, df_no_relay, df_fcquic_relay, df_app_relay, add_labels=True):
    if len(df_no_relay) > 0:
        ax.ecdf(
            (df_no_relay["y_LATENCY"] / 1000),
            label="No relay" if add_labels else None,
            color=NO_RELAY_COLOR,
            linestyle=NO_RELAY_LINESTYLE,
            lw=LINEWIDTH,
        )
    if len(df_fcquic_relay) > 0:
        ax.ecdf(
            (df_fcquic_relay["y_LATENCY"] / 1000),
            label="FCQUIC Relay" if add_labels else None,
            color=FCQUIC_RELAY_COLOR,
            linestyle=FCQUIC_RELAY_LINESTYLE,
            lw=LINEWIDTH + 0.2,
        )
    if len(df_app_relay) > 0:
        ax.ecdf(
            (df_app_relay["y_LATENCY"] / 1000),
            label="Application Relay" if add_labels else None,
            color=APP_RELAY_COLOR,
            linestyle=APP_RELAY_LINESTYLE,
            lw=LINEWIDTH,
        )


def process_and_plot(data_df, out_path, name, data_size, inset=False):
    # remove outliers
    # q = data_df["y_LATENCY"].quantile(0.995)
    # print(f"Outlier threshold: {q}")
    # data_df = data_df[data_df["y_LATENCY"] < q]

    # filter dataframes based on RELAY_VERSION, mappings:
    df_no_relay = data_df[data_df["RELAY_VERSION"] == "none"]
    df_fcquic_relay = data_df[data_df["RELAY_VERSION"] == "RELAY"]
    df_app_relay = data_df[data_df["RELAY_VERSION"] == "APP_RELAY"]

    len_no_relay = len(df_no_relay)
    len_fcquic_relay = len(df_fcquic_relay)
    len_app_relay = len(df_app_relay)

    print(f"No relay samples: {len_no_relay}")
    print(f"FCQUIC relay samples: {len_fcquic_relay}")
    print(f"APP relay samples: {len_app_relay}")

    if "run_index" in data_df.columns:
        print("Per run breakdown")
        for test_name, df_test in [
            ("none", df_no_relay),
            ("RELAY", df_fcquic_relay),
            ("APP_RELAY", df_app_relay),
        ]:
            if len(df_test) > 0:
                print(f"{test_name}:")
                run_counts = df_test.groupby("test_index").size()
                for run_idx, count in run_counts.items():
                    print(f"  Run {run_idx}: {count} samples")

    global_len = min(len_app_relay, len_no_relay, len_fcquic_relay)
    print(f"min length of the dataframes: {global_len}")

    sns.set_style("whitegrid")
    fig = plt.figure(figsize=(7, 7))
    latexify(nb_subplots_line=1, fig_height=7, fig_width=7)

    ax = plt.gca()
    _plot_ecdfs(ax, df_no_relay, df_fcquic_relay, df_app_relay, add_labels=True)

    plt.ylabel("Probability of occurence", fontsize=15)

    # Add data size to title if available
    data_size_str = f" (data size: {data_size} bytes)" if data_size is not None else ""
    plt.title(
        f"Cumulative distribution of latency, {data_size_str}",
        fontsize=15,
    )
    plt.xlabel("Latency (ms)", fontsize=15)
    # plt.xlim(left=0)
    plt.ylim(0, 1)

    plt.legend()
    plt.grid(True, alpha=0.3)

    # zoomed inset
    if inset:
        axins = ax.inset_axes([0.58, 0.05, 0.40, 0.25])  # type: ignore
        axins.set_facecolor("white")
        for spine in axins.spines.values():
            spine.set_edgecolor("black")
            spine.set_linewidth(1.0)

        _plot_ecdfs(axins, df_no_relay, df_fcquic_relay, df_app_relay, add_labels=False)

        all_latencies = (
            pd.concat(
                [
                    df_no_relay["y_LATENCY"],
                    df_fcquic_relay["y_LATENCY"],
                    df_app_relay["y_LATENCY"],
                ]
            )
            / 1000
        )

        # choose the latencies to show by setting x_min to the start (e.g., min or quantile(0.8)...)
        # then set x_max accordingly, so if xmin was quantile(0.9), we set xmax to max and this will show the upper boddy of the cdf (here the worst 10 of the latencies)
        # if we do the opposite and set xmin to min, then we set xmax to quantile(0.5), this will show the lower body of the cdf (here the lowest 50% of the latencies)

        # x_min = float(all_latencies.quantile(0.95))
        # x_max = float(all_latencies.max())
        # axins.set_xlim(x_min, x_max)
        # axins.set_ylim(0.95, 1.001)

        x_min = float(all_latencies.min())
        x_max = float(all_latencies.quantile(0.90))
        axins.set_xlim(x_min, x_max)
        axins.set_ylim(0, 0.90)

        axins.tick_params(labelsize=10)
        axins.grid(True, alpha=0.3)

        ax.legend(loc="center right", fontsize=13, framealpha=0.9)
    else:
        ax.legend(loc="lower right", fontsize=13, framealpha=0.9)

    fig.tight_layout()

    data_size_str = f"_datasize_{data_size}" if data_size is not None else ""
    inset_str = "_inset" if inset else ""

    plt.savefig(
        f"{out_path}/cdf_{name}{data_size_str}{inset_str}.svg",
        bbox_inches="tight",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser("plots")
    parser.add_argument("file_path", type=file_path)
    parser.add_argument("out_path", type=dir_path)
    parser.add_argument("name", type=str)

    parser.add_argument("ack_rate_path", type=dir_path)
    parser.add_argument("cpu_csv_path", type=file_path)

    parser.add_argument(
        "--inset",
        action="store_true",
        help="add a zoomed in inset for the cdfs",
    )
    args = parser.parse_args()

    main(
        args.file_path,
        args.out_path,
        args.name,
        args.inset,
        args.ack_rate_path,
        args.cpu_csv_path,
    )
