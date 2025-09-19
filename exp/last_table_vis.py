import os

import matplotlib.pyplot as plt
import numpy as np

# Create output directory if it doesn't exist
output_dir = "exp/data/paper"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Using the global configuration settings you provided
FIG_SIZE = (10, 4)
fontsize = 27

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.weight"] = "bold"
plt.rcParams["xtick.labelsize"] = fontsize - 6
plt.rcParams["ytick.labelsize"] = fontsize - 2
plt.rcParams["axes.labelsize"] = fontsize
plt.rcParams["axes.labelweight"] = "bold"
plt.rcParams["legend.fontsize"] = fontsize - 5

# Data from the table II
type_i_data = {
    "name": ["qft-20", "qft-30", "qft-40", "qft-50"],
    "baseline": [144, 335, 599, 933],
    "class": [0, 0, 256, 576],
}

type_ii_data = {
    "name": [
        "cc-12",
        "cc-32",
        "pe-20",
        "pe-30",
        "pe-40",
        "pe-50",
        "random-20",
        "random-30",
        "random-40",
        "random-50",
    ],
    "baseline": [24, 120, 125, 309, 591, 911, 339, 882, 1500, 2691],
    "class": [6, 6, 19, 29, 309, 619, 39, 111, 912, 1812],
}

average_data = {
    "name": ["Type-I Average", "Type-II Average"],
    "baseline": [(144 + 335 + 599 + 933) / 4, 749.20],
    "class": [(0 + 0 + 256 + 576) / 4, 386.20],
}

# Calculate improvement percentages for Type-I
type_i_improvement_data = {"name": type_i_data["name"] + ["Average"], "improvement": []}

for i in range(len(type_i_data["name"])):
    if type_i_data["baseline"][i] == 0:
        type_i_improvement_data["improvement"].append(0)
    else:
        improvement = (
            (type_i_data["baseline"][i] - type_i_data["class"][i])
            / type_i_data["baseline"][i]
            * 100
        )
        type_i_improvement_data["improvement"].append(improvement)

# Calculate average improvement for Type-I
type_i_total_baseline = sum(type_i_data["baseline"])
type_i_total_class = sum(type_i_data["class"])
type_i_average_improvement = (
    (type_i_total_baseline - type_i_total_class) / type_i_total_baseline * 100
)
type_i_improvement_data["improvement"].append(type_i_average_improvement)

# Calculate improvement percentages for Type-II
type_ii_improvement_data = {
    "name": type_ii_data["name"] + ["Average"],
    "improvement": [],
}

for i in range(len(type_ii_data["name"])):
    improvement = (
        (type_ii_data["baseline"][i] - type_ii_data["class"][i])
        / type_ii_data["baseline"][i]
        * 100
    )
    type_ii_improvement_data["improvement"].append(improvement)

# Calculate average improvement for Type-II
type_ii_average_improvement = (749.20 - 386.20) / 749.20 * 100
type_ii_improvement_data["improvement"].append(type_ii_average_improvement)

# 1. Improvement Percentage in Type-I Benchmarks
plt.figure(figsize=FIG_SIZE)
x = np.arange(len(type_i_improvement_data["name"]))

# Use a different color for Type-I improvement - Use a blue color
bars = plt.bar(
    x,
    type_i_improvement_data["improvement"],
    width=0.7,
    color="#3366cc",
    edgecolor="black",
    linewidth=1,
)

# Highlight the average bar with a different color
bars[-1].set_color("#00008B")  # Darker blue for average

# Add percentage labels with 45-degree rotation, keeping two decimal places
for i, bar in enumerate(bars):
    height = bar.get_height()
    plt.text(
        bar.get_x() + bar.get_width() / 2.0,
        height + 1,
        f"{type_i_improvement_data['improvement'][i]:.2f}%",  # Changed to .2f to keep two decimal places
        ha="center",
        va="bottom",
        fontsize=fontsize
        - 15,  # Changed from fontsize - 12 to fontsize - 15 (from 15 to 12)
        fontweight="bold",
        rotation=45,
    )

plt.xlabel("")
plt.ylabel("Improvement (%)", fontsize=fontsize - 5)
plt.xticks(x, type_i_improvement_data["name"], rotation=45, ha="right")
plt.ylim(0, 105)  # Set y-axis limit from 0 to 105 to accommodate labels
plt.grid(axis="y", linestyle="--", alpha=0.7)
# plt.tight_layout()
plt.savefig(
    os.path.join(output_dir, "type_i_improvement_percentage.pdf"), bbox_inches="tight"
)
plt.show()

# 2. Improvement Percentage in Type-II Benchmarks
plt.figure(figsize=FIG_SIZE)
x = np.arange(len(type_ii_improvement_data["name"]))

# Keep the orange color for Type-II improvement
bars = plt.bar(
    x,
    type_ii_improvement_data["improvement"],
    width=0.7,
    color="#ff7300",
    edgecolor="black",
    linewidth=1,
)

# Highlight the average bar with a different color
bars[-1].set_color("#B22222")  # Darker red/orange for average

# Add percentage labels with 45-degree rotation, keeping two decimal places
for i, bar in enumerate(bars):
    height = bar.get_height()
    plt.text(
        bar.get_x() + bar.get_width() / 2.0,
        height + 1,
        f"{type_ii_improvement_data['improvement'][i]:.2f}%",  # Changed to .2f to keep two decimal places
        ha="center",
        va="bottom",
        fontsize=fontsize
        - 15,  # Changed from fontsize - 12 to fontsize - 15 (from 15 to 12)
        fontweight="bold",
        rotation=45,
    )

plt.xlabel("")
plt.ylabel("Improvement (%)", fontsize=fontsize - 5)
plt.xticks(x, type_ii_improvement_data["name"], rotation=45, ha="right")
plt.grid(axis="y", linestyle="--", alpha=0.7)
# plt.tight_layout()
plt.savefig(
    os.path.join(output_dir, "type_ii_improvement_percentage.pdf"), bbox_inches="tight"
)
plt.show()
