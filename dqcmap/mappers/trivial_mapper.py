import logging
from collections import Counter
from typing import List

from z3 import And, Bool, If, Optimize, Or, Sum, sat, set_param

from dqcmap.basemapper import BaseMapper
from dqcmap.exceptions import DqcMapException

logger = logging.getLogger(__name__)


class TrivialMapper(BaseMapper):
    def run(self) -> List[int]:
        ctrl_to_pq = self._ctrl_conf.ctrl_to_pq
        cif_pairs = self._circ_prop.cif_pairs
        cif_pairs = [tuple(p) for p in cif_pairs]
        n_logical = self._circ_prop.num_qubits

        # Set a fixed random seed for Z3
        set_param("smt.random_seed", 42)

        logger.info("Initializing solver...")
        optimizer = Optimize()

        n_physical = sum(len(qubits) for qubits in ctrl_to_pq.values())

        logger.info(
            f"Creating variables for {n_logical} logical qubits and {n_physical} physical qubits..."
        )
        x = [[Bool(f"x_{i}_{j}") for j in range(n_physical)] for i in range(n_logical)]

        logger.info("Adding constraints...")
        # Each logical qubit must be mapped to exactly one physical qubit
        for i in range(n_logical):
            optimizer.add(Sum([If(x[i][j], 1, 0) for j in range(n_physical)]) == 1)

        # Each physical qubit can be mapped to at most one logical qubit
        for j in range(n_physical):
            optimizer.add(Sum([If(x[i][j], 1, 0) for i in range(n_logical)]) <= 1)

        # Each controller can control only its assigned physical qubits
        for ctrl, qubits in ctrl_to_pq.items():
            optimizer.add(
                Sum([If(x[i][j], 1, 0) for i in range(n_logical) for j in qubits])
                <= len(qubits)
            )

        # Count occurrences of each CIF pair
        pair_counts = Counter(cif_pairs)

        # Objective function: Maximize the weighted number of CIF pairs on the same controller
        logger.info("Setting up objective function...")
        objective = Sum(
            [
                If(
                    Or(
                        [
                            And(x[i][p1], x[j][p2])
                            for ctrl, qubits in ctrl_to_pq.items()
                            for p1 in qubits
                            for p2 in qubits
                        ]
                    ),
                    pair_counts[(i, j)],
                    0,
                )
                for i, j in pair_counts.keys()
            ]
        )

        optimizer.maximize(objective)

        # Solve the problem
        if optimizer.check() == sat:
            model = optimizer.model()
            mapping = [-1] * n_logical
            for i in range(n_logical):
                for j in range(n_physical):
                    if model.evaluate(x[i][j]):
                        mapping[i] = j
            objective_value = model.evaluate(objective).as_long()
            logger.debug(
                f"Fount initial mapping: {mapping}, with objective_value: {objective_value}"
            )
            return mapping

        raise DqcMapException("Mapping failed to find a intial mapping")
