import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

################# Matplotlib Global Conf #########################
fontsize = 25

# plt.rcParams["text.usetex"] = True
plt.rcParams["xtick.labelsize"] = fontsize - 2
plt.rcParams["ytick.labelsize"] = fontsize - 2
# plt.rcParams['ztick.labelsize'] = fontsize - 2
# plt.rcParams["xtick.major.pad"] = -1
# plt.rcParams["ytick.major.pad"] = -1
plt.rcParams["axes.labelsize"] = fontsize
plt.rcParams["axes.labelweight"] = "bold"
plt.rcParams["legend.fontsize"] = fontsize // 2
## below not working
# plt.rcParams["patch.edgecolor"] = "black"
# plt.rcParams["patch.linewidth"] = 1

################# Matplotlib Global Conf #########################


def read_and_prepare_csvs(directory):
    csv_files = [
        os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".csv")
    ]
    all_data = []
    for file in csv_files:
        df = pd.read_csv(file)
        df["source_file"] = os.path.basename(file)
        all_data.append(df)
    return pd.concat(all_data, ignore_index=True)


def normalize_data(df):
    baseline_data = df[df["compiler_type"] == "baseline"]
    for index, row in df.iterrows():
        baseline_row = baseline_data[(baseline_data["num_qubits"] == row["num_qubits"])]
        for col in ["percent_inter", "runtime", "depth"]:
            if not baseline_row.empty:
                df.at[index, col] /= baseline_row[col].values[0]
    return df


def plot_data(df):
    ## currently we have a fixed source_file to label mapping
    label_dict = {
        "baseline_dqcswap_dqcmap_opt_3.csv": "baseline",
        "multi_ctrl_dqcswap_decay_opt_3.csv": "map",
        "multi_ctrl_dqcswap_dqcmap_opt_3.csv": "map + route",
        "multi_ctrl_dqcswap_decay_opt_6.csv": "map + layout",
        "multi_ctrl_dqcswap_dqcmap_opt_6.csv": "map + layout + route",
    }

    # unique_files = df["source_file"].unique()
    unique_files = [
        "baseline_dqcswap_dqcmap_opt_3.csv",
        "multi_ctrl_dqcswap_decay_opt_3.csv",
        "multi_ctrl_dqcswap_dqcmap_opt_3.csv",
        "multi_ctrl_dqcswap_decay_opt_6.csv",
        "multi_ctrl_dqcswap_dqcmap_opt_6.csv",
    ]
    colors = plt.cm.tab20(np.linspace(0, 1, len(unique_files)))
    color_map = dict(zip(unique_files, colors))
    width = 0.15  # Bar width

    metrics = ["percent_inter", "runtime", "depth"]
    num_qubits_values = sorted(df["num_qubits"].unique())

    for metric in metrics:
        fig, ax = plt.subplots(figsize=(10, 6))
        for j, file in enumerate(unique_files):
            file_data = df[df["source_file"] == file]
            nqs = file_data["num_qubits"]
            values = file_data[metric]
            indices = [num_qubits_values.index(nq) + j * width for nq in nqs]
            ax.bar(
                indices,
                values,
                width,
                color=color_map[file],
                label=label_dict[file],
                edgecolor="black",
                linewidth=1,
            )

        ax.set_xlabel("Number of Qubits")
        ax.set_ylabel(metric)
        # ax.set_title(f"{metric.capitalize()} Comparison")
        ax.set_xticks(
            [
                x + width * (len(unique_files) - 1) / 2
                for x in range(len(num_qubits_values))
            ]
        )
        ax.set_xticklabels(num_qubits_values)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.1), ncol=3)

        plt.tight_layout()
        plt.show()
        fig.savefig(f"{metric}.svg", bbox_inches="tight")


def main(directory):
    df = read_and_prepare_csvs(directory)
    normalized_df = normalize_data(df)
    plot_data(normalized_df)


if __name__ == "__main__":
    directory = "exp/"
    main(directory)
