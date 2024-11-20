# Introduction

This repository contains the source code and scripts to reproduce the results presented in the paper: "CLASS: A Controller-Centric Layout Synthesizer for Dynamic Quantum Circuits".

# Build and Installation

To set up the environment and build the project, follow the steps below:

1. Install Rust: Follow the official guide (https://www.rust-lang.org/learn/get-started) to install Rust.
2. Create a Python Virtual Environment: You can use `venv`, Anaconda, or Miniconda to create a new environment. Example using conda:
   - `conda create -y -n class python=3.11.9`
   - `conda activate class`
3. Install the Project: Run the following command to install the project in editable mode:
   - `pip install -e .`

# Running Tests

To verify that everything is set up correctly, you can run the tests for both Python and Rust components:

- Python Tests: Run the following command to execute the Python test suite:
  - `pytest tests/`
- Rust Tests: Run the following command to execute the Rust tests:
  - `cargo test --no-default-features`
  - For more information on testing Rust components, see this guide (https://github.com/Qiskit/qiskit/blob/1.1.1/CONTRIBUTING.md#testing-rust-components).

# Usage

We provide a script (`exp/bench.py`) to evaluate the performance of our approach across various benchmarks. Below is a description of the script's options:

- `--n`: Number of qubits.
- `--p`: Probability of generating conditional gates when creating a random benchmark.
- `--seed`: Random seed for reproducibility.
- `--c`: Number of circuits for a given number of qubits, useful for averaging performance across multiple random circuits.
- `--log`: Enable logging for debugging purposes.
- `--debug-only`: Specify which module should output debug information.
- `--comp`: Compiler method or a list of methods (separated by `,`). Options:
  - `baseline`: Qiskit with SABRE.
  - `multi_ctrl`: The proposed controller-centric synthesizer (CLASS).
- `--ctrl`: Number of controllers (each managing a subgraph of the coupling map).
- `--parallel`: Run circuits in parallel (disable when `--log` is enabled).
- `--opt`: Optimization level for `multi_ctrl` compiler (different from Qiskit transpiler). `opt=6` represents the full CLASS implementation.
- `--t`: Scaling factor for two-qubit gate time.
- `--rt`: Routing method (gate scheduler). Options:
  - `sabre`: The baseline method.
  - `dqcswap`: The ICCS-Aware method in CLASS.
- `--rt-trial`: Number of parallel swap trials during routing.
- `--heuristic`: Heuristic for `dqcswap` routing. The default value `dqcmap` represents the methodology presented in Algorithm 3 of the paper.
- `--wr`: Whether to write results to a CSV file.
- `--wr-path`: Directory to save the result files.
- `--qasm`: Directory containing QASM benchmark files.
- `--bench`: Type of benchmark (e.g., `random`, `pe`, `qft`, `cc`) or a file with a list of benchmarks.
- `--st`, `--show-mapper-runtime`: Print runtime of mapper (initial placement).

For more details, run:
- `python exp/bench.py -h`

# Reproducing Results

To reproduce the results from the paper, use the following commands (assuming a Unix environment):

## Table I

- `python exp/bench.py --comp baseline,multi_ctrl --ctrl 4 --parallel 1 --opt 6 --t 0.2 --rt dqcswap --bench exp/benchmarks.lst --wr 1 --wr-path exp/data/paper`

- Generate LaTeX table code:
  - `python exp/gen_main_res_table.py exp/data/paper/benchmarks.lst_baseline_multi_ctrl_dqcswap_dqcmap_opt_6_ctrl_4.csv`

## Impact of Controller Count (Figure 6)

- `for c in 4 5 6 7 8; do python exp/bench.py --n 30 --p 0.5 --c 1 --comp baseline,multi_ctrl --opt 6 --t 0.1 --bench random --parallel 1 --ctrl $c; done | tee exp/data/paper/ctrl_num_impact.txt`

- `python exp/plot_num_ctrl_impact.py exp/data/paper/ctrl_num_impact.txt`

## Runtime Analysis (Fig. 7)

- `python exp/bench.py --n 20,40,60,80,100 --p 0.9 --comp multi_ctrl --bench qft --c 1 --st 1 --parallel 0 --ctrl 5 | tee exp/data/paper/runtime_analysis_same_ctrl.txt`

- `python exp/plot_runtime_analysis.py exp/data/paper/runtime_analysis_same_ctrl.txt`

# Contributing

To ensure your contributions meet project standards, please set up pre-commit hooks:

- `pip install pre-commit`
- `pre-commit install`

Before committing changes, run:
- `git add . && pre-commit run`
