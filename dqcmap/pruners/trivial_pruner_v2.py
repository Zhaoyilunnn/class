import copy
import logging
import random

from qiskit.transpiler.coupling import CouplingMap

from dqcmap.exceptions import DqcMapException
from dqcmap.pruners.trivial_pruner import TrivialPruner
from dqcmap.utils.cm import CmHelper

logger = logging.getLogger(__name__)


class TrivialPrunerV2(TrivialPruner):
    def run(self):
        """
        Just randomly remove some connections between different subgraphs,
        note that we should keep the coupling map connected

        Compared with TrivialPruner, this version cut both directions of edges
        """
        # First generate a list containing only single direction edges (between different subgraphs)
        sd_edges = CmHelper.to_single_direct(self._edges)
        num_pruned = int(len(sd_edges) * self._prob)

        if num_pruned == 0:
            logger.warning(
                "No edges to prune, consider increasing the pruning probability"
            )

        # randomly shuffle the edges and obtain the first N edges for pruning
        for i in range(100):
            random.seed(self._base_seed + i)
            random.shuffle(sd_edges)
            pruned_edges = sd_edges[:num_pruned]

            # deepcopy is used to avoid modifying original coupling_map
            cm_lst = copy.deepcopy(self._cm)

            for e in pruned_edges:
                cm_lst.remove(e)
                # also remove the reversed one (if exists)
                reverse = [e[1], e[0]]
                if reverse in cm_lst:
                    cm_lst.remove(reverse)

            # Got a pruned cm, return it if it is still connected
            cm = CouplingMap(cm_lst)

            if cm.is_connected():
                return cm_lst

        raise DqcMapException(
            f"{self.__class__} failed to generate a valid prunning pattern to keep the original coupling map connected"
        )
