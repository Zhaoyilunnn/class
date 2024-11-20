# Introduction

This repository contains the source code and scripts to reproduce the results in the paper titled: "CLASS: A Controller-Centric Layout Synthesizer for Dynamic Quantum Circuits".

# Build and Install

1. Install [Rust](https://www.rust-lang.org/learn/get-started) in your system.
2. Create a new virtual environment using python `venv`/anaconda/miniconda. Example using conda: `conda create -y -n class python=3.11.9`
3. Build and install: `pip install -e .`


# Testing

- Python: `pytest tests/`
- Rust: `cargo test --no-default-features`. See this [guide](https://github.com/Qiskit/qiskit/blob/1.1.1/CONTRIBUTING.md#testing-rust-components)


# Usage

We have built a script `exp/bench.py` to test the performance on variaty of benchmarks. The detailed explanations for all options are listed as below.


- `--n`: Number of qubits.
- `--p`: Probability of generating conditional gates when generating a randomized benchmark.
- `--seed`: Random seed.
- `--c`: Number of circuits for certain `num_qubits`, this option is only useful when testing random circuits, for which you can generate a number of circuits with the same number of qubits ang obtain the averaged performance.
- `--log`: Whether to output log for debugging.
- `--debug-only`: Specifying which module to output debut info.
- `--comp`: Compiler method or a list of compiler methods split by `,`.
  - `baseline`: Qiskit with SABRE.
  - `multi_ctrl`: The proposed controller-centric synthesizer.
- `--ctrl`: Number of controllers. Each controller is configured to manage a subgraph of the coupling map.
- `--parallel`: Whether to run each circuit in parallel. Note that you need to turn off this flag when `--log` is on.
- `--opt`: Optimization level used in dqcmap compiler. Note that this is different from qiskit transipler optimization level.
- `--t`: The scaling factor of two-qubit gate time. State-of-the-art two-qubit gate time is much smaller than public available devices. So use this config to simulate most recent devices.
- `--rt`: Routing method (gate scheduling). For baseline, it will always be set to `sabre`, for `multi_ctrl` it will be this argument.
- `--rt-trial`: Number of parallel swap trials during routing.
- `--heuristic`: Heuristic for dqcswap routing.
- `--wr`: Whether to write results to csv.
- `--wr-path`: Directory for saving result files.
- `--qasm`: Directory of qasm benchmarks.
- `--bench`: Type of benchmarks. Now we support `random`, `pe`, `qft`, and `cc`. You can also specify a file consisting of a list of benchmarks. Note that if this argument is a file, its name cannot be the same as a specific benchmark name. And if given a file, random circuits will generate only one instance.
- `--st --show-mapper-runtime`: Whether to print runtime of mapper (initial placement).


See also `python exp/bench.py -h`.

# Results Reproduction

## Table I

```
python exp/bench.py --comp baseline,multi_ctrl --ctrl 4 --parallel 1 --opt 6 --t 0.2 --rt dqcswap --bench exp/benchmarks.lst --wr 1 --wr-path exp/data/paper

# Then use following scripts to generate latex table code
python exp/gen_main_res_table.py exp/data/paper/benchmarks.lst_baseline_multi_ctrl_dqcswap_dqcmap_opt_6_ctrl_4.csv
```

## Impact of Controller Num (Fig. 6)

```
for c in 4 5 6 7 8; do python exp/bench.py --n 30 --p 0.5 --c 1 --comp baseline,multi_ctrl --opt 6 --t 0.1 --bench random --parallel 1 --ctrl $c; done | tee exp/data/paper/ctrl_num_impact.txt
python exp/plot_num_ctrl_impact.py exp/data/paper/ctrl_num_impact.txt

```

## Runtime Analysis

```
python exp/bench.py --n 20,40,60,80,100 --p 0.9 --comp multi_ctrl --bench qft --c 1 --st 1 --parallel 0 --ctrl 5 | tee exp/data/paper/runtime_analysis_same_ctrl.txt
python exp/plot_runtime_analysis.py exp/data/paper/runtime_analysis_same_ctrl.txt
```


# Contribution

```
pip install pre-commit
git add . && pre-commit
```
