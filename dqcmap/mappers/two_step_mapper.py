from typing import Dict, List, Set, Tuple

from dqcmap.basemapper import BaseMapper
from dqcmap.circuit_prop import CircProperty
from dqcmap.controller import ControllerConfig
from dqcmap.mappers.heuristic_graphpartition_mapper import HeuristicMapper
from dqcmap.mappers.intra_controller_optimizer import IntraControllerOptimizer
from dqcmap.mappers.iter_KL_mapper import KLMapper


class TwoStepMapper(BaseMapper):
    def __init__(self, ctrl_conf: ControllerConfig, circ_prop: CircProperty):
        # first mapper is used to minimize the cif pairs across controllers
        self.heuristic_mapper = HeuristicMapper(ctrl_conf, circ_prop)
        # self.KL_mapper = KLMapper(ctrl_conf, circ_prop)
        # print("----------------------start intra_optimizer----------------------")
        # The intra_controller_optimizer is used to optimize the initial mapping within each controller by minimizing the number of connections between qubits for two-qubit gates.
        self.intra_optimizer = IntraControllerOptimizer(ctrl_conf, circ_prop)
        # print("----------------------end intra_optimizer----------------------")

    def run(self) -> List[int]:
        initial_mapping = self.heuristic_mapper.run()
        # initial_mapping = self.KL_mapper.run()
        # print("initial_mapping", initial_mapping)
        optimized_mapping = self.intra_optimizer.run(initial_mapping)
        # print("optimized_mapping", optimized_mapping)
        return optimized_mapping
