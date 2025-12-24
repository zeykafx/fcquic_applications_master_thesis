#!/usr/bin/env python3
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


def main():
    df = pd.read_csv("npf_out.csv")

    sns.set_style("whitegrid")
    plt.figure(figsize=(10, 6))

    # get the non null values from the y_LATENCY column and drop any NAN
    latency_values = df["y_LATENCY"].dropna().to_numpy()

    if len(latency_values) > 0:
        sorted_values = np.sort(latency_values)
        # compute CDF values
        cdf = np.arange(1, len(sorted_values) + 1) / len(sorted_values)

        plt.plot(
            sorted_values,
            cdf,
            label="Latency",
            color=sns.color_palette("husl")[0],
            linewidth=2,
        )

    plt.xlabel("Latency (ms)", fontsize=12)
    plt.ylabel("CDF", fontsize=12)
    plt.title("CDF of agg. Latency", fontsize=14)
    plt.legend(loc="lower right", fontsize=10)
    plt.xlim(left=0)
    plt.ylim(0, 1)

    plt.grid(True, alpha=0.3)

    plt.tight_layout()

    plt.savefig("latency_cdf_aggregated.png", dpi=300, bbox_inches="tight")
    plt.savefig("latency_cdf_aggregated.svg", bbox_inches="tight")
    print("saved plogs")


if __name__ == "__main__":
    main()
