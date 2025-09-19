import os
import re
import sys

import pandas as pd

MAP_COMPILER_TYPE = {"baseline": "Baseline", "multi\\_ctrl": "\\name{}"}

BENCHMARKS = ["qft", "cc", "pe", "random"]


# Function to read CSV data from a specified file path
def read_csv_from_file(filepath):
    return pd.read_csv(filepath)


# Function to escape underscores in strings for LaTeX
def escape_underscore(text):
    return re.sub(r"_", r"\\_", text)


# Function to generate LaTeX table grouped by compiler type
def generate_grouped_latex_table(df):
    # Sort the dataframe by 'bench_name' and 'compiler_type' for better grouping
    df.sort_values(by=["bench_name", "compiler_type"], inplace=True)

    # Get unique compiler types to create column groups
    compiler_types = df["compiler_type"].unique()

    # Start building the LaTeX table
    # Define the table structure: 1 column for benchmark name, 1 for num_qubits, and 3 columns per compiler type (Runtime, Depth, CIF Pairs)
    latex_code = (
        r"""\begin{table*}[ht]
    \centering
    \caption{Comparison between \name{} and baseline.}
    \begin{tabular}{ll"""
        + "ccc" * len(compiler_types)
        + r"""}
        \toprule
        \textbf{Benchmark} & \textbf{Qubits} & """
        + " & ".join(
            [
                f"\\multicolumn{{3}}{{c}}{{{MAP_COMPILER_TYPE[escape_underscore(compiler)]}}}"
                for compiler in compiler_types
            ]
        )
        + r""" \\
        """
        + " ".join(
            [
                f"\\cmidrule(lr){{{3 + i * 3}-{5 + i * 3}}}"
                for i in range(len(compiler_types))
            ]
        )
        + "\n"
    )

    # Add subheaders for each compiler's metrics (Runtime, Depth, CIF Pairs)
    latex_code += (
        " " * 8
        + "& & "
        + " & ".join([r"\# Operations & Depth & \# ICCS" for _ in compiler_types])
        + r" \\"
        + "\n"
    )
    latex_code += r"        \midrule" + "\n"

    # Iterate over each unique benchmark name
    for bench_name in BENCHMARKS:
        # Get the number of qubits for this benchmark
        nq_lst = df[df["bench_name"] == bench_name]["num_qubits"].unique()

        for i, nq in enumerate(nq_lst):
            latex_code += f"        {escape_underscore(bench_name)} & {nq}"

            for compiler in compiler_types:
                # Extract the row matching this benchmark and compiler type
                row = df[
                    (df["bench_name"] == bench_name)
                    & (df["compiler_type"] == compiler)
                    & (df["num_qubits"] == nq)
                ]

                if not row.empty:
                    num_op = row.iloc[0]["num_op"]
                    depth = row.iloc[0]["depth"]
                    num_cif_pairs = row.iloc[0]["num_cif_pairs"]
                    latex_code += f" & {num_op} & {int(depth)} & {int(num_cif_pairs)}"
                else:
                    latex_code += " & - & - & -"  # Use "-" if no data available

            if i == len(nq_lst) - 1 and bench_name == "qft":
                latex_code += r" \\ \midrule" + "\n"
            else:
                latex_code += r" \\" + "\n"

    # Calculate average values for each compiler type
    avg_values = {}
    for compiler in compiler_types:
        avg_values[compiler] = {
            "num_op": df[
                (df["compiler_type"] == compiler) & (df["bench_name"] != "qft")
            ]["num_op"].mean(),
            "depth": df[
                (df["compiler_type"] == compiler) & (df["bench_name"] != "qft")
            ]["depth"].mean(),
            "num_cif_pairs": df[
                (df["compiler_type"] == compiler) & (df["bench_name"] != "qft")
            ]["num_cif_pairs"].mean(),
        }

    # Add average row to the LaTeX table
    latex_code += r"        \midrule" + "\n"
    latex_code += r"        \textbf{Average} & -"
    for compiler in compiler_types:
        avg_num_op = avg_values[compiler]["num_op"]
        avg_depth = avg_values[compiler]["depth"]
        avg_num_cif_pairs = avg_values[compiler]["num_cif_pairs"]
        latex_code += f" & {avg_num_op:.2f} & {avg_depth:.2f} & {avg_num_cif_pairs:.2f}"
    latex_code += r" \\" + "\n"

    # Close the table
    latex_code += r"""        \bottomrule
    \end{tabular}
    \label{tab:main_res}
\end{table*}"""

    return latex_code


def wrap_latex_document(table_code):
    return (
        r"""\documentclass{article}
\usepackage{booktabs}
\usepackage{geometry}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{graphicx}
\usepackage{longtable}
\usepackage{float}
\usepackage{hyperref}
\geometry{margin=1in}
\newcommand{\name}{CLASS}
\begin{document}
"""
        + table_code
        + "\n\\end{document}\n"
    )


# Specify the path to your CSV file
if len(sys.argv) != 2:
    print(f"Usage: python {sys.argv[0]} <path-to-res>")
    sys.exit(1)

file_path = sys.argv[1]

# Read the CSV data from the specified file
df = read_csv_from_file(file_path)

# Generate the LaTeX code
latex_table_code = generate_grouped_latex_table(df)

# Wrap in a full LaTeX document
latex_full_doc = wrap_latex_document(latex_table_code)

# Write to a .tex file in exp/paper/ directory
output_dir = "exp/data/paper"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "main_res_table.tex")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(latex_full_doc)

# Also print the LaTeX code to stdout
print(latex_full_doc)
