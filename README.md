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

```
python exp/bench.py --n 20 --c 10 --parallel 1 --comp baseline,multi_ctrl --opt 2 --t 0.2 --p 0.9
```

Options
- `--n`: number of qubits
- `--c`: number of random circuits for averaging performance
- `--parallel`: whether those `c` circuits run in parallel
- `--comp`: compilation method. baseline refers to qiskit default transpilation, multi\_ctrl refers to our controller-aware compilation.
- `--opt`: optimization level of multi\_ctrl
- `--t`: scaling factor of two-qubit duration, since current simulated device has a much longer 2-q duration than SOTA.
- `--p`: percentage of condition pairs in a quantum circuit
