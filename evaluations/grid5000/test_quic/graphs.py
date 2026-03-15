import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

df = pd.read_csv(f"./npf-out/2026-03-13 23:35:11.554159.csv")

fig, ax = plt.subplots(figsize=(8, 5))
sns.lineplot(
    data=df,
    x="ADDITIONAL_DATA_SIZE",
    y="y_LATENCY",
    markers=True,
    errorbar="sd",
    ax=ax,
)
ax.set_xlabel("Additional Data Size")
ax.set_ylabel("Latency (ms)")
ax.set_title("Latency vs Additional Data Size")
plt.tight_layout()
plt.savefig("latency_vs_size.png", dpi=150)
# plt.show()

plt.figure()
fig, ax = plt.subplots(figsize=(8, 5))
sns.ecdfplot(data=df, x="y_LATENCY", ax=ax)
ax.set_xlabel("Latency (ms)")
ax.set_title("CDF of Latency")
plt.tight_layout()
plt.savefig("latency_cdf.png", dpi=150)
# plt.show()
