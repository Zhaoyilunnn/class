import time
from typing import List

from dqcmap.basemapper import BaseMapper
from dqcmap.circuit_prop import CircProperty
from dqcmap.controller import ControllerConfig

from .heuristic_graphpartition_mapper import HeuristicMapper
from .iter_KL_mapper import KLMapper
from .trivial_mapper import TrivialMapper
from .two_step_mapper import TwoStepMapper

MAPPERS = {
    "trivial": TrivialMapper,
    "heuristic": HeuristicMapper,
    "kl_partition": KLMapper,
    "two_step": TwoStepMapper,
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
    show_runtime: bool = False,
    **mapper_config,
):
    """Partition the coupling_map into subgraphs and prune the edges between subgraphs"""
    mapper = MapperProvider.get(mapper_name, *(ctrl_conf, circ_prop), **mapper_config)
    start_time = time.perf_counter()
    layout = mapper.run()
    if show_runtime:
        print(f"Runtime of mapper is {time.perf_counter() - start_time}")
    return layout
