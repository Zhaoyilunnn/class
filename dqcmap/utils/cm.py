"""A helper module for analyzing coupling map"""

from typing import List

import rustworkx
from qiskit import QuantumCircuit
from qiskit.transpiler.coupling import CouplingMap


class CmHelper:
    """Helper class for analyzing coupling map"""

    @staticmethod
    def to_rw_graph(coupling_map: List[List[int]]):
        """Transform coupling map to a rustworkx graph"""
        graph = rustworkx.PyGraph()
        nodes = set()

        for e in coupling_map:
            nodes.update(e)
        for node in nodes:
            graph.add_node(node)

        for e in coupling_map:
            graph.add_edge(e[0], e[1], None)

        return graph

    @staticmethod
    def gen_trivial_connected_region(qc: QuantumCircuit, coupling_map: List[List[int]]):
        """
        Generate a randomized connected region of coupling map
        """
        cm = CouplingMap(couplinglist=coupling_map)
        cm.connected_components()
        # img = cm.draw()
        # img.save("test.png")
        return list(range(qc.num_qubits))
