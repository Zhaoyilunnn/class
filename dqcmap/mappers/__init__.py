from typing import List

from dqcmap.basemapper import BaseMapper
from dqcmap.circuit_prop import CircProperty
from dqcmap.controller import ControllerConfig

from .heuristic_graphpartition_mapper import HeuristicMapper
from .iter_KL_mapper import KLMapper
from .trivial_mapper import TrivialMapper

MAPPERS = {
    "trivial": TrivialMapper,
    "heuristic": HeuristicMapper,
    "kl_partition": KLMapper,
}


class MapperProvider:
    @classmethod
    def get(cls, name, *args, **kwargs) -> BaseMapper:
        """"""
        return MAPPERS[name](*args, **kwargs)


def mapping(
    ctrl_conf: ControllerConfig,
    circ_prop: CircProperty,
    mapper_name: str = "trivial",
    **mapper_config,
):
    """Partition the coupling_map into subgraphs and prune the edges between subgraphs"""
    mapper = MapperProvider.get(mapper_name, *(ctrl_conf, circ_prop), **mapper_config)
    return mapper.run()
