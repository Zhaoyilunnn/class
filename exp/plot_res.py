import argparse
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

METRICS = ["percent_inter", "runtime", "depth", "num_cif_pairs"]

################# Matplotlib Global Conf #########################
FIG_SIZE = (15, 5)
fontsize = 27

# plt.rcParams["text.usetex"] = True
plt.rcParams["xtick.labelsize"] = fontsize - 6
plt.rcParams["ytick.labelsize"] = fontsize - 2
# plt.rcParams['ztick.labelsize'] = fontsize - 2
# plt.rcParams["xtick.major.pad"] = -1
# plt.rcParams["ytick.major.pad"] = -1
plt.rcParams["axes.labelsize"] = fontsize
plt.rcParams["axes.labelweight"] = "bold"
plt.rcParams["legend.fontsize"] = fontsize - 10
## below not working
# plt.rcParams["patch.edgecolor"] = "black"
# plt.rcParams["patch.linewidth"] = 1

################# Matplotlib Global Conf #########################


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--d",
        default="exp",
        type=str,
        help="Specify the directory to store plotted figures.",
    )
    return parser.parse_args()


ARGS = get_args()


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
        baseline_row = baseline_data[(baseline_data["bench_name"] == row["bench_name"])]
        for col in METRICS:
            if not baseline_row.empty:
                df.at[index, col] /= baseline_row[col].values[0]
    return df


def plot_data(df):
    # unique_files = df["source_file"].unique()
    impls = [
        "baseline",
        # "map",
        # "map+route",
        "map+layout",
        "map+layout+route",
    ]
    colors = plt.cm.tab20(np.linspace(0, 1, len(impls)))
    color_map = dict(zip(impls, colors))
    width = 0.15  # Bar width

    metrics = METRICS
    bench_names = sorted(df["bench_name"].unique())
    bench_names.append("avg")

    for metric in metrics:
        fig, ax = plt.subplots(figsize=FIG_SIZE)
        for j, impl in enumerate(impls):
            file_data = df[df["impl"] == impl]
            if file_data.empty:
                continue
            # bns = file_data["bench_name"]  # benchmark names
            values = [
                file_data[file_data["bench_name"] == bn][metric].values[0]
                for bn in bench_names[:-1]
            ]
            avg_val = np.mean(values)
            values.append(avg_val)
            indices = [bench_names.index(b) + j * width for b in bench_names]
            bars = ax.bar(
                indices,
                values,
                width,
                color=color_map[impl],
                label=impl,
                edgecolor="black",
                linewidth=1,
            )

            # Adding text labels above the bars
            if impl != "baseline":
                bar = bars[-1]
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    height,
                    f"{height:.2f}",
                    ha="center",
                    va="bottom",
                    fontsize=fontsize // 2,
                    rotation=45,
                    color="red",
                )

        ax.set_xlabel("Benchmark")
        ax.set_ylabel(metric)
        # ax.set_title(f"{metric.capitalize()} Comparison")
        ax.set_xticks(
            [x + width * (len(impls) - 1) / 2 for x in range(len(bench_names))],
        )
        ax.set_xticklabels(bench_names, rotation=45)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.1), ncol=3)

        plt.tight_layout()
        plt.show()
        file_path = os.path.join(ARGS.d, f"{metric}.svg")
        fig.savefig(file_path, bbox_inches="tight")


def main(directory):
    df = read_and_prepare_csvs(directory)
    normalized_df = normalize_data(df)
    plot_data(normalized_df)


if __name__ == "__main__":
    directory = ARGS.d
    if not os.path.exists(directory):
        os.mkdir(directory)
    main(directory)
