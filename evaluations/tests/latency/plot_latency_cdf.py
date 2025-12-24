#!/usr/bin/env python3
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


def main():
    df = pd.read_csv("npf_out-TIME.csv")

    latency_columns = [col for col in df.columns if col.startswith("y_LATENCY-CLIENT")]

    sns.set_style("whitegrid")
    plt.figure(figsize=(10, 6))

    colors = sns.color_palette("husl", len(latency_columns))

    # plot CDF for each client/receiver
    for i, col in enumerate(latency_columns):
        # extract the client name from column name (e.g., 'y_LATENCY-CLIENT3' -> 'Client 3')
        client_name = col.replace("y_LATENCY-", "").replace("CLIENT", "Client ")

        latency_values = df[col].dropna().values

        if len(latency_values) > 0:
            # sort the values for CDF
            sorted_values = np.sort(latency_values)
            # compute CDF values
            cdf = np.arange(1, len(sorted_values) + 1) / len(sorted_values)

            plt.plot(
                sorted_values, cdf, label=client_name, color=colors[i], linewidth=2
            )

    plt.xlabel("Latency (ms)", fontsize=12)
    plt.ylabel("CDF", fontsize=12)
    plt.title("CDF of Latency for All Receivers", fontsize=14)
    plt.legend(loc="lower right", fontsize=10)
    plt.xlim(left=0)
    plt.ylim(0, 1)

    plt.grid(True, alpha=0.3)

    plt.tight_layout()

    plt.savefig("latency_cdf.png", dpi=300, bbox_inches="tight")
    # plt.savefig("latency_cdf.pdf", bbox_inches="tight")
    print("plots saved")


if __name__ == "__main__":
    main()
