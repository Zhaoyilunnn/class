from typing import List

from dqcmap.basemapper import BaseMapper
from dqcmap.circuit_prop import CircProperty
from dqcmap.controller import ControllerConfig
from dqcmap.mappers.heuristic_graphpartition_mapper import HeuristicMapper
from dqcmap.mappers.intra_controller_optimizer import RandomIntraControllerMapper


class TwoStepMapper(BaseMapper):
    def __init__(self, ctrl_conf: ControllerConfig, circ_prop: CircProperty):
        super().__init__(ctrl_conf, circ_prop)
        # First mapper is used to minimize the cif pairs across controllers
        self.heuristic_mapper = HeuristicMapper(ctrl_conf, circ_prop)
        # Second mapper randomly reassigns qubits within each controller
        self.random_intra_mapper = RandomIntraControllerMapper(ctrl_conf, circ_prop)

    def run(self) -> List[int]:
        # First step: Apply HeuristicMapper
        initial_mapping = self.heuristic_mapper.run()

        # Second step: Apply RandomIntraControllerMapper
        optimized_mapping = self.random_intra_mapper.run(initial_mapping)

        return optimized_mapping
