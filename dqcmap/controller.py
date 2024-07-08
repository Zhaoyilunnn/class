from typing import List

import rustworkx


class Controller:
    def __init__(self, coupling_map: List[List]):
        graph = rustworkx.PyGraph()
        nodes = set()

        for e in coupling_map:
            nodes.update(e)
        for node in nodes:
            graph.add_node(node)

        for e in coupling_map:
            graph.add_edge(e[0], e[1], None)

        self._graph = graph

    def gen_controller_regions(self, region_size: int):
        """
        Args:
            region_size (int): Number of qubits that are controlled by the same controller
        """
        regions = rustworkx.connected_components(self._graph)
        print(regions)
