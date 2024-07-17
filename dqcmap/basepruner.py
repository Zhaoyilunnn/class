from abc import ABC, abstractmethod
from typing import Any, List


class BasePruner(ABC):
    def __init__(self, sg_nodes_lst, coupling_map: List[List[int]]):
        """Initialization of a pruner

        Args:
            sg_nodes_lst: List of subgraph node lists.
            coupling_map: coupling map in couplinglist format.
        """
        self._cm = coupling_map

        # mapping between physical qubit index and subgraph index
        self._pq2sg = None

        # edges between different subgraphs
        self._edges = self._get_edges_inter_sg(sg_nodes_lst, coupling_map)

    def _get_edges_inter_sg(self, sg_nodes_lst, coupling_map):
        """Analyze the connections between different subgraphs"""
        pq2sg = {}
        edges = []
        for sg_id, sg_nodes in enumerate(sg_nodes_lst):
            for pq in sg_nodes:
                pq2sg[pq] = sg_id

        for e in coupling_map:
            assert len(e) == 2
            sg_0, sg_1 = pq2sg[e[0]], pq2sg[e[1]]
            if sg_0 != sg_1:
                edges.append(e)

        self._pq2sg = pq2sg

        return edges

    @abstractmethod
    def run(self) -> Any:
        """Prune the edges between subgraphs and return the couplinglist after pruning"""
