from typing import List

from dqcmap.basepruner import BasePruner

from .trivial_pruner import TrivialPruner
from .trivial_pruner_v2 import TrivialPrunerV2

PRUNERS = {
    "trivial": TrivialPruner,
    "trivial_v2": TrivialPrunerV2,
}


class PrunerProvider:
    @classmethod
    def get(cls, name, *args, **kwargs) -> BasePruner:
        """"""
        return PRUNERS[name](*args, **kwargs)


@staticmethod
def virtual_prune(
    coupling_map: List[List[int]],
    sg_nodes_lst: List[List[int]],
    pruning_method: str = "trivial",
    **pruner_configs,
):
    """Partition the coupling_map into subgraphs and prune the edges between subgraphs"""
    pruner = PrunerProvider.get(
        pruning_method, *(sg_nodes_lst, coupling_map), **pruner_configs
    )
    return pruner.run()
