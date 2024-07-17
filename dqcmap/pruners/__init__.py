from dqcmap.basepruner import BasePruner

from .trivial_pruner import TrivialPruner

PRUNERS = {
    "trivial": TrivialPruner,
}


class PrunerProvider:
    @classmethod
    def get(cls, name, *args, **kwargs) -> BasePruner:
        """"""
        return PRUNERS[name](*args, **kwargs)
