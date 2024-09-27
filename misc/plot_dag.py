import argparse

import matplotlib.pyplot as plt
from qiskit.circuit import QuantumCircuit
from qiskit.converters import circuit_to_dag
from qiskit.visualization.dag_visualization import dag_drawer


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--f",
        default="benchmarks/veriq-benchmark/dynamic/pe/dqc_pe_5.qasm",
        type=str,
        help="Path to qasm.",
    )
    return parser.parse_args()


ARGS = get_args()


def main():
    qc = QuantumCircuit.from_qasm_file(ARGS.f)
    dag = circuit_to_dag(qc)
    dag_drawer(dag, filename="dag.svg")
    qc.draw(output="latex", filename="qc.pdf")


if __name__ == "__main__":
    main()
