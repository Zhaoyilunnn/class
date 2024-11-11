# Prerequisite

```
apt-get install graphviz
```

# Development

## Build and Install

```
pip install -e .
```

## Testing


### Python
```
pytest tests/
```

### Rust

According to this [guide](https://github.com/Qiskit/qiskit/blob/1.1.1/CONTRIBUTING.md#testing-rust-components)

```
cargo test --no-default-features
```

# pre-commit

```
pip install pre-commit
git add . && pre-commit
```

# experiment

## random circuit
```
python exp/bench.py --n 30 --p 0.9 --c 1 --comp baseline,multi_ctrl --parallel 0 --opt 6 --t 0.2 --rt dqcswap --rt-trial 1 --heuristic decay --bench random --ctrl 5
```

## DQC phase estimation (PE)

```
python exp/bench.py --n 30 --p 0.9 --c 1 --comp baseline,multi_ctrl --parallel 0 --opt 6 --t 0.2 --rt dqcswap --rt-trial 1 --heuristic decay --bench pe --ctrl 5
```

## Options
- `--n`: number of qubits
- `--c`: number of random circuits for averaging performance
- `--parallel`: whether those `c` circuits run in parallel
- `--comp`: compilation method. baseline refers to qiskit default transpilation, multi\_ctrl refers to our controller-aware compilation.
- `--opt`: optimization level of multi\_ctrl
- `--t`: scaling factor of two-qubit duration, since current simulated device has a much longer 2-q duration than SOTA.
- `--p`: percentage of condition pairs in a quantum circuit


Run `python exp/bench.py -h` for detailed instructions and explanations of all command line arguments.

## main results

```
bash exp/run_main.sh
```


## Table I

```
python exp/bench.py --comp baseline,multi_ctrl --ctrl 4 --parallel 1 --opt 6 --t 0.2 --rt dqcswap --bench exp/benchmarks.lst --wr 1 --wr-path exp/data/paper

# Then use following scripts to generate latex table code
python exp/gen_main_res_table.py exp/data/paper/benchmarks.lst_baseline_multi_ctrl_dqcswap_dqcmap_opt_6_ctrl_4.csv
```
