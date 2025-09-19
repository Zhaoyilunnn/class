from typing import List

from dqcmap.basemapper import BaseMapper
from dqcmap.circuit_prop import CircProperty
from dqcmap.controller import ControllerConfig
from dqcmap.mappers.intra_controller_optimizer import RandomIntraControllerMapper
from dqcmap.mappers.iter_KL_mapper import KLMapper


class TwoStepMapper(BaseMapper):
    def __init__(self, ctrl_conf: ControllerConfig, circ_prop: CircProperty):
        super().__init__(ctrl_conf, circ_prop)
        # self.heuristic_mapper = HeuristicMapper(ctrl_conf, circ_prop)
        self.iter_KL_mapper = KLMapper(ctrl_conf, circ_prop)
        self.random_intra_mapper = RandomIntraControllerMapper(ctrl_conf, circ_prop)

    def run(self, num_iterations: int = 20, initial_seed: int = 42) -> List[List[int]]:
        mappings = []

        # First step: Apply HeuristicMapper (run only once) or KLMapper
        # initial_mapping = self.heuristic_mapper.run()
        initial_mapping = self.iter_KL_mapper.run()

        for i in range(num_iterations):
            # Set a unique but reproducible seed for each iteration.
            iteration_seed = initial_seed + i

            # Step 2: Apply RandomIntraControllerMapper
            optimized_mapping = self.random_intra_mapper.run(
                initial_mapping, seed=iteration_seed
            )

            mappings.append(optimized_mapping)

        return mappings
