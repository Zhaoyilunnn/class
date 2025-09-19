import argparse
import os

from qiskit import qasm3

from dqcmap.utils import get_synthetic_dqc


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", default=10, type=int, help="Number of qubits.")
    parser.add_argument(
        "--p", default=0.5, type=float, help="Ratio of conditional operations."
    )

    return parser.parse_args()


def main():
    args = get_args()
    num_qubits = args.n
    depth = args.n
    cond_ratio = args.p
    ratio = int(args.p * 100)  # just for file naming
    for idx in range(10):
        qc = get_synthetic_dqc(
            num_qubits, depth, cond_ratio=cond_ratio, use_qiskit=False, seed=1900 + idx
        )
        filename = f"random_{num_qubits}_{depth}_{ratio}_type_0_{idx}.qasm"
        filepath = os.path.join("benchmarks", filename)
        with open(filepath, "w") as f:
            qasm3.dump(qc, f)


if __name__ == "__main__":
    main()
