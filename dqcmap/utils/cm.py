"""A helper module for analyzing coupling map"""

import logging
from typing import List, Sequence, Tuple

import rustworkx as rx
from qiskit import QuantumCircuit
from qiskit.transpiler.coupling import CouplingMap
from rustworkx.visit import BFSVisitor
from rustworkx.visualization import graphviz_draw

logger = logging.getLogger(__name__)


class VertexVisitor(BFSVisitor):
    def __init__(self):
        self.vertexes = []

    def discover_vertex(self, v: int):
        self.vertexes.append(v)


def _debug_rx_graph(graph: rx.PyDiGraph | rx.PyGraph):
    for n in graph.node_indices():
        print(f"node index: {n}")
    for e in graph.edge_list():
        print(f"edge: {e}")


def _draw_graphs(
    graph_lst: List[rx.PyGraph], name_prefix: str = "g", img_type: str = "svg"
):
    for i, g in enumerate(graph_lst):
        graphviz_draw(g, image_type=img_type, filename=f"{name_prefix}_{i}.{img_type}")


class CmHelper:
    """Helper class for analyzing coupling map"""

    @staticmethod
    def to_rx_graph(coupling_map: List[List[int]]):
        """Transform coupling map to a rustworkx graph"""
        graph = rx.PyGraph()
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
        _ = CouplingMap(couplinglist=coupling_map)
        # cm.connected_components()
        # graphviz_draw(cm.graph, image_type="svg", filename="test.svg")
        return list(range(qc.num_qubits))

    @staticmethod
    def gen_random_connected_regions(
        coupling_map, region_size: int = 10, save_fig: bool = False
    ):
        """Generate connected regions with approximately equal size

        Args:
            coupling_map: Coupling map in couplinglist format.
            region_size: Number of qubits in a connected region.
            save_fig: Whether to save figures to disk.

        Return:
            (subgraphs, sg_nodes_lst): A tuple of subgraphs, ``subgraphs`` are
            a set of rx.PyGraph, ``sg_nodes_lst`` is a list of subgraph node lists
        """
        g = rx.PyGraph()

        def _to_rx_edge_list() -> Sequence[Tuple[int, int]]:
            e_lst = []
            for x in coupling_map:
                assert len(x) == 2
                e_lst.append(tuple(x))
            return e_lst

        g.extend_from_edge_list(_to_rx_edge_list())

        if not rx.is_connected(g):
            raise ValueError(
                "`gen_trivial_connected_regions` can only be used for connected coupling_map"
            )

        if save_fig:
            _draw_graphs([g])

        # Name the graph
        # for i in g.node_indices():
        #     g[i] = f"Q_{i}"

        subgraphs: List[rx.PyGraph] = []
        sg_nodes_lst = []  # list of nodes in each subgraph
        nodes_to_process = set(g.node_indices())

        while nodes_to_process:
            start_node = next(iter(nodes_to_process))

            # BFS
            visitor = VertexVisitor()
            rx.bfs_search(g, [start_node], visitor)
            bfs_nodes = visitor.vertexes

            # Generate subgraph
            subgraph_nodes = bfs_nodes[:region_size]
            subgraph = g.subgraph(subgraph_nodes, preserve_attrs=True).copy()
            subgraphs.append(subgraph)
            nodes_to_process.difference_update(subgraph_nodes)
            sg_nodes_lst.append(subgraph_nodes)

            for n in subgraph_nodes:
                g.remove_node(n)

            logger.debug(f"Found subgraph: {subgraph_nodes}")

        if save_fig:
            _draw_graphs(subgraphs, name_prefix="sg")
        return subgraphs, sg_nodes_lst

    @staticmethod
    def to_single_direct(coupling_map: List[List[int]]):
        seen = set()
        res = []

        for e in coupling_map:
            assert len(e) == 2
            tup_e = tuple(e)
            reverse = (e[1], e[0])

            if tup_e not in seen and reverse not in seen:
                seen.add(tup_e)
                res.append(e)

        return res
