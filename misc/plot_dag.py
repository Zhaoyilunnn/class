import argparse
from typing import List

import matplotlib.pyplot as plt
import networkx as nx
from qiskit.circuit import QuantumCircuit
from qiskit.converters import circuit_to_dag
from qiskit.visualization.dag_visualization import dag_drawer

from dqcmap.circuit_prop import CircProperty
from dqcmap.utils.misc import get_synthetic_dqc


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--f",
        default="benchmarks/veriq-benchmark/dynamic/pe/dqc_pe_5.qasm",
        type=str,
        help="Path to qasm.",
    )
    parser.add_argument(
        "--s",
        type=int,
        default=11,
        help="random seed for generating randomized dynamic quantum circuit.",
    )
    return parser.parse_args()


ARGS = get_args()


def plot_cif_graph(cif_pairs: List[List[int]]):
    G = nx.Graph()

    for edge in cif_pairs:
        node1 = f"q_{edge[0]}"
        node2 = f"q_{edge[1]}"
        if G.has_edge(node1, node2):
            G[node1][node2]["weight"] += 1
        else:
            G.add_edge(node1, node2, weight=1)

    pos = nx.spring_layout(G)
    weights = nx.get_edge_attributes(G, "weight")
    labels = {e: w for e, w in weights.items()}

    nx.draw(
        G,
        pos,
        with_labels=True,
        node_color="lightblue",
        edge_color="gray",
        node_size=700,
        width=3,
    )
    nx.draw_networkx_edge_labels(G, pos, edge_labels=labels)

    # plt.title("Graph with Edge Weights")
    plt.savefig("cif_graph.svg")
    plt.show()


def main():
    if ARGS.f == "random":
        qc = get_synthetic_dqc(
            6, 2, use_rb=False, cond_ratio=0.8, use_qiskit=False, seed=ARGS.s
        )
    else:
        qc = QuantumCircuit.from_qasm_file(ARGS.f)
    dag = circuit_to_dag(qc)
    dag_drawer(dag, filename="dag.svg")
    qc.draw(output="latex", filename="qc.pdf")

    cif_pairs = CircProperty(qc).cif_pairs

    plot_cif_graph(cif_pairs)


if __name__ == "__main__":
    main()
