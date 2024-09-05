import copy
import logging
import random
from typing import List, Optional

from qiskit.transpiler.coupling import CouplingMap

from dqcmap.basepruner import BasePruner
from dqcmap.exceptions import DqcMapException

logger = logging.getLogger(__name__)


# FIXME: current impl does not guarantee retaining all nodes
class MappingAwarePruner(BasePruner):
    """
    For each inter-subgraph edge, check if there exist cross subgraph CNOTs and score this edge
    based on the number of CNOTs,

    While selecting edges to prune, prioritize small-score edges.
    """

    def __init__(
        self,
        sg_nodes_lst,
        coupling_map,
        prob: float = 0.5,
        seed: int = 1900,
        mapping: Optional[List[int]] = None,
        multi_op_list: Optional[List[List[int]]] = None,
    ):
        """
        Args:
            sg_nodes_lst: List of subgraph nodes.
            coupling_map: coupling map in the format of couplinglist.
            prob: probability to prune an edge.
            seed: random seed.
            mapping: the logical to physical mapping as list.
                E.g., [1, 2, 3] means logical q0 -> physical q1; logical q1 -> physical q2; logical q2 -> physical q3
            multi_op_list: list of multi-qubit operations. Each operation is represented as a list of indexed of the
                corresponding logical qubits.
        """
        super().__init__(sg_nodes_lst, coupling_map)

        if mapping is None or multi_op_list is None:
            raise ValueError(
                f"`mapping` and `multi_op_list` must be set when using MappingAwarePruner"
            )

        if not (prob >= 0 and prob < 0.5):
            raise ValueError(
                f"Pruning probability should be in [0, 0.5) when using MappingAwarePruner"
            )
        self._prob = prob
        self._base_seed = seed
        self._scores = self._score_edges(mapping, multi_op_list)

    def _score_edges(self, mapping: List[int], multi_op_list: List[List[int]]):
        """Score each edge based on the number of multi qubit operations on it"""
        pq2lq = {}
        for lq, pq in enumerate(mapping):
            pq2lq[pq] = lq

        scores = []
        for e in self._edges:
            score = 0
            lq0 = pq2lq[e[0]]
            lq1 = pq2lq[e[1]]
            for op in multi_op_list:
                if lq0 in op and lq1 in op:
                    score += 1
            scores.append((e, score))
        return scores

    def run(self):
        """
        Just randomly remove some connections between different subgraphs,
        note that we should keep the coupling map connected
        """
        num_pruned = int(len(self._edges) * self._prob)

        if num_pruned == 0:
            logger.warning(
                "No edges to prune, consider increasing the pruning probability"
            )

        # sort edges based on edge score
        num_candidate = int(len(self._edges) * 2 * self._prob)
        self._scores.sort(key=lambda item: item[1])
        candidate_edges = [self._scores[i][0] for i in range(num_candidate)]

        for i in range(10):
            pruned_edges = candidate_edges[:num_pruned]

            # deepcopy is used to avoid modifying original coupling_map
            # because we need to generate pruned one multiple times until
            # we find a pruned cm that is still connected
            cm_lst = copy.deepcopy(self._cm)

            for e in pruned_edges:
                cm_lst.remove(e)
                # also remove the reversed one (if exists)
                reverse = [e[1], e[0]]
                if reverse in cm_lst:
                    cm_lst.remove(reverse)

            # return if coupling map is still connected
            cm = CouplingMap(cm_lst)

            if cm.is_connected():
                return cm_lst

            random.seed(self._base_seed + i)
            random.shuffle(candidate_edges)

        raise DqcMapException(
            f"{self.__class__} failed to generate a valid prunning pattern to keep the original coupling map connected"
        )
