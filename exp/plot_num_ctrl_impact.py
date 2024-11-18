import sys

import matplotlib.pyplot as plt
import numpy as np

################# Matplotlib Global Conf #########################
FIG_SIZE = (15, 5)
fontsize = 27

# plt.rcParams["text.usetex"] = True
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.weight"] = "bold"
plt.rcParams["xtick.labelsize"] = fontsize - 6
plt.rcParams["ytick.labelsize"] = fontsize - 2
# plt.rcParams['ztick.labelsize'] = fontsize - 2
# plt.rcParams["xtick.major.pad"] = -1
# plt.rcParams["ytick.major.pad"] = -1
plt.rcParams["axes.labelsize"] = fontsize
plt.rcParams["axes.labelweight"] = "bold"
plt.rcParams["legend.fontsize"] = fontsize - 5
## below not working
# plt.rcParams["patch.edgecolor"] = "black"
# plt.rcParams["patch.linewidth"] = 1

################# Matplotlib Global Conf #########################


def parse_data_from_txt(file_path):
    # Dictionary to store extracted data for baseline and multi_ctrl
    data = {"baseline": [], "multi_ctrl": []}

    # Read the txt file
    with open(file_path, "r") as file:
        for line in file:
            # Split the line by tabs
            values = line.strip().split("\t")

            # Skip lines that are headers or empty
            if values[0] == "bench_name" or len(values) < 10:
                continue

            # Extract the compiler_type and num_cif_pairs
            compiler_type = values[2]
            num_cif_pairs = float(values[8])

            # Add the num_cif_pairs value to the respective list
            if compiler_type == "baseline":
                data["baseline"].append(num_cif_pairs)
            elif compiler_type == "multi_ctrl":
                data["multi_ctrl"].append(num_cif_pairs)

    return data


def plot_comparison(data):
    baseline_values = data["baseline"]
    multi_ctrl_values = data["multi_ctrl"]

    # labels = [f"Run {i+1}" for i in range(len(baseline_values))]
    labels = [4, 5, 6, 7, 8]

    x = np.arange(len(labels))  # the label locations
    width = 0.35  # the width of the bars

    fig, ax = plt.subplots(figsize=(10, 4))
    rects1 = ax.bar(
        x - width / 2,
        baseline_values,
        width,
        label="Baseline",
        edgecolor="black",
        linewidth=1,
        hatch="/",
        color="#2A9D8C",
    )
    rects2 = ax.bar(
        x + width / 2,
        multi_ctrl_values,
        width,
        label="CLASS",
        edgecolor="black",
        linewidth=1,
        color="#E66F51",
    )

    # Add some text for labels, title and custom x-axis tick labels, etc.
    ax.set_xlabel("k")
    ax.set_ylabel("# ICCS")
    # ax.set_title("Comparison of Num CIF Pairs for Baseline and Multi_ctrl")
    ax.set_xticks(x)
    # ax.set_xticklabels(labels, rotation=45)
    ax.set_xticklabels(labels)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.15), ncol=2)

    fig.tight_layout()
    plt.show()

    plt.savefig("num_ctrl_impact.pdf")


if __name__ == "__main__":
    # Parse data from txt file
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <path-to-ctrl-impact-res-log>")
        sys.exit(1)
    file_path = sys.argv[1]  # Replace with your actual file path
    data = parse_data_from_txt(file_path)

    # Plot the comparison bar chart
    plot_comparison(data)
