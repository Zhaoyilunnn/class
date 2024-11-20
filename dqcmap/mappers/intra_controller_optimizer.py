import random
from collections import defaultdict
from typing import Dict, List, Set, Tuple

import networkx as nx

from dqcmap.basemapper import BaseMapper
from dqcmap.circuit_prop import CircProperty
from dqcmap.controller import ControllerConfig


class IntraControllerOptimizer(BaseMapper):
    def __init__(self, ctrl_conf: ControllerConfig, circ_prop: CircProperty):
        super().__init__(ctrl_conf, circ_prop)
        self.ctrl_conf = self._ctrl_conf
        self.circ_prop = self._circ_prop
        self.ctrl_to_pq = self._ctrl_conf.ctrl_to_pq
        self.n_logical = self._circ_prop.num_qubits
        self.n_controllers = len(self.ctrl_to_pq)
        self.all_physical_qubits = [
            pq for pqs in self.ctrl_to_pq.values() for pq in pqs
        ]
        self.graph = self.build_two_qubit_graph()
        self.coupling_map = self._ctrl_conf._cm
        self.cross_controller_edges = self.identify_cross_controller_edges()
        self.coupling_graph = nx.Graph(self.coupling_map)
        self.shortest_paths = self.precompute_shortest_paths()

    def precompute_shortest_paths(self) -> Dict[Tuple[int, int], int]:
        shortest_paths = {}
        for source in self.coupling_graph.nodes():
            paths = nx.single_source_shortest_path_length(self.coupling_graph, source)
            for target, length in paths.items():
                shortest_paths[(source, target)] = length
                shortest_paths[(target, source)] = length
        return shortest_paths

    def identify_cross_controller_edges(self) -> Dict[int, Set[int]]:
        cross_edges = defaultdict(set)
        for edge in self.coupling_map:
            ctrl1 = self.get_controller(edge[0])
            ctrl2 = self.get_controller(edge[1])
            if ctrl1 != ctrl2:
                cross_edges[edge[0]].add(edge[1])
                cross_edges[edge[1]].add(edge[0])
        return cross_edges

    def build_two_qubit_graph(self) -> Dict[int, Set[int]]:
        graph = defaultdict(set)
        for q1, q2 in self.circ_prop.two_qubit_gates:
            graph[q1].add(q2)
            graph[q2].add(q1)
        return graph

    def count_cross_controller_gates(
        self, initial_mapping: List[int]
    ) -> Dict[int, int]:
        cross_gates = defaultdict(int)
        for q1, q2 in self.circ_prop.two_qubit_gates:
            if self.get_controller(initial_mapping[q1]) != self.get_controller(
                initial_mapping[q2]
            ):
                cross_gates[q1] += 1
                cross_gates[q2] += 1
        return cross_gates

    def run(self, initial_mapping: List[int]) -> List[int]:
        self.cross_controller_gates = self.count_cross_controller_gates(initial_mapping)
        ctrl_to_logical = self.get_ctrl_to_logical(initial_mapping)
        optimized_mapping = initial_mapping.copy()
        optimized_mapping_dict = {
            i: optimized_mapping[i] for i in range(self.n_logical)
        }

        for ctrl, logical_qubits in ctrl_to_logical.items():
            physical_qubits = self.ctrl_to_pq[ctrl]
            # print(f"Optimizing controller {ctrl}: logical_qubits={logical_qubits}, physical_qubits={physical_qubits}")
            intra_mapping = self.optimize_controller(
                ctrl, logical_qubits, physical_qubits, optimized_mapping_dict
            )
            optimized_mapping_dict.update(intra_mapping)

        # Handle any unmapped qubits
        unmapped_logical = set(range(self.n_logical)) - set(
            optimized_mapping_dict.keys()
        )
        available_physical = set(self.all_physical_qubits) - set(
            optimized_mapping_dict.values()
        )

        for logical in unmapped_logical:
            if available_physical:
                physical = available_physical.pop()
                optimized_mapping[logical] = physical
                print(f"Remapped logical qubit {logical} to physical qubit {physical}")
            else:
                print(f"Error: Unable to map logical qubit {logical}")
                return initial_mapping

        final_mapping = [optimized_mapping_dict[i] for i in range(self.n_logical)]
        # print(f"Final optimized mapping: {final_mapping}")
        return final_mapping

    def get_ctrl_to_logical(self, mapping: List[int]) -> Dict[int, List[int]]:
        ctrl_to_logical = defaultdict(list)
        for logical, physical in enumerate(mapping):
            ctrl = self.get_controller(physical)
            ctrl_to_logical[ctrl].append(logical)
        return ctrl_to_logical

    # TODO: need to optimize the mapping for the controller
    def optimize_controller(
        self,
        ctrl: int,
        logical_qubits: List[int],
        physical_qubits: List[int],
        optimized_mapping_dict: Dict[int, int],
    ) -> Dict[int, int]:
        n_logical = len(logical_qubits)
        n_physical = len(physical_qubits)

        # print(f"Optimizing controller {ctrl}: n_logical: {n_logical}, n_physical: {n_physical}")

        sorted_qubits = sorted(
            logical_qubits,
            key=lambda q: self.cross_controller_gates.get(q, 0),
            reverse=True,
        )
        edge_physical_qubits = [
            pq for pq in physical_qubits if pq in self.cross_controller_edges
        ]
        non_edge_physical_qubits = [
            pq for pq in physical_qubits if pq not in self.cross_controller_edges
        ]
        non_edge_physical_qubits.sort(
            key=lambda pq: sum(
                self.shortest_paths.get((pq, edge_pq), 1000)
                for edge_pq in edge_physical_qubits
            )
        )

        initial_mapping = {}
        for q in sorted_qubits:
            if edge_physical_qubits:
                initial_mapping[q] = edge_physical_qubits.pop(0)
            # if edge_physical_qubits is empty, we will check non_edge_physical_qubits to use
            elif non_edge_physical_qubits:
                initial_mapping[q] = non_edge_physical_qubits.pop(0)
            else:
                print(
                    f"Error: Unable to map logical qubit {q}, physical qubits in the controller {ctrl} are not enough"
                )
                return initial_mapping
        best_mapping = initial_mapping
        best_score = self.evaluate_intra_mapping(
            ctrl, best_mapping, optimized_mapping_dict
        )

        for _ in range(1000):  # You can adjust the number of iterations
            current_mapping = best_mapping.copy()

            if len(current_mapping) > 1:
                q1, q2 = random.sample(list(current_mapping.keys()), 2)
                current_mapping[q1], current_mapping[q2] = (
                    current_mapping[q2],
                    current_mapping[q1],
                )

            current_score = self.evaluate_intra_mapping(
                ctrl, current_mapping, optimized_mapping_dict
            )

            if current_score < best_score:
                best_mapping = current_mapping
                best_score = current_score

        # print(f"Optimized mapping for controller {ctrl}: {best_mapping}")
        return best_mapping

    def evaluate_intra_mapping(
        self,
        ctrl: int,
        single_ctrl_mapping: Dict[int, int],
        optimized_mapping_dict: Dict[int, int],
    ) -> float:
        score = 0
        mapping = optimized_mapping_dict.copy()
        mapping.update(single_ctrl_mapping.copy())

        for q1, q2 in self.circ_prop.two_qubit_gates:
            if q1 in mapping and q2 in mapping:
                p1 = mapping[q1]
                p2 = mapping[q2]
                ctrl1 = self.get_controller(p1)
                ctrl2 = self.get_controller(p2)

                if ctrl1 != ctrl2:
                    distance = self.shortest_paths.get((p1, p2), 1000)
                    score += distance * 3

        return score

    def get_controller(self, physical_qubit: int) -> int:
        for ctrl, pqs in self.ctrl_to_pq.items():
            if physical_qubit in pqs:
                return ctrl
        raise ValueError(f"Physical qubit {physical_qubit} not found in any controller")


class RandomIntraControllerMapper(BaseMapper):
    """
    Randomly map logical qubits to physical qubits within each controller.

    This mapper takes an initial mapping and randomly reassigns logical qubits
    to physical qubits within the same controller. It maintains the distribution
    of logical qubits across controllers from the initial mapping, but shuffles
    their assignments within each controller.

    Attributes:
        ctrl_to_pq (Dict[int, List[int]]): Mapping of controllers to physical qubits.
        n_logical (int): Number of logical qubits in the circuit.
        n_controllers (int): Number of controllers in the quantum device.
        all_physical_qubits (List[int]): List of all physical qubit ids.

    Methods:
        run(initial_mapping: List[int], seed: int = None) -> List[int]:
            Performs the random intra-controller mapping.
        get_ctrl_to_logical(mapping: List[int]) -> Dict[int, List[int]]:
            Groups logical qubits by their assigned controllers.
        get_controller(physical_qubit: int) -> int:
            Determines which controller a physical qubit belongs to.
    """

    def __init__(self, ctrl_conf: ControllerConfig, circ_prop: CircProperty):
        super().__init__(ctrl_conf, circ_prop)
        self.ctrl_to_pq = self._ctrl_conf.ctrl_to_pq
        self.n_logical = self._circ_prop.num_qubits
        self.n_controllers = len(self.ctrl_to_pq)
        self.all_physical_qubits = [
            pq for pqs in self.ctrl_to_pq.values() for pq in pqs
        ]

    def run(self, initial_mapping: List[int], seed: int = None) -> List[int]:
        if seed is not None:
            random.seed(seed)
        ctrl_to_logical = self.get_ctrl_to_logical(initial_mapping)
        new_mapping = [-1] * self.n_logical

        for ctrl, logical_qubits in ctrl_to_logical.items():
            physical_qubits = self.ctrl_to_pq[ctrl].copy()
            random.shuffle(physical_qubits)

            for logical_qubit in logical_qubits:
                if physical_qubits:
                    new_mapping[logical_qubit] = physical_qubits.pop()
                else:
                    print(f"Error: Not enough physical qubits for controller {ctrl}")
                    return initial_mapping

        # Handle any unmapped qubits
        unmapped_logical = [i for i, pq in enumerate(new_mapping) if pq == -1]
        available_physical = set(self.all_physical_qubits) - set(new_mapping)

        for logical in unmapped_logical:
            if available_physical:
                physical = available_physical.pop()
                new_mapping[logical] = physical
                print(f"Remapped logical qubit {logical} to physical qubit {physical}")
            else:
                print(f"Error: Unable to map logical qubit {logical}")
                return initial_mapping

        return new_mapping

    def get_ctrl_to_logical(self, mapping: List[int]) -> Dict[int, List[int]]:
        ctrl_to_logical = defaultdict(list)
        for logical, physical in enumerate(mapping):
            ctrl = self.get_controller(physical)
            ctrl_to_logical[ctrl].append(logical)
        return ctrl_to_logical

    def get_controller(self, physical_qubit: int) -> int:
        for ctrl, pqs in self.ctrl_to_pq.items():
            if physical_qubit in pqs:
                return ctrl
        raise ValueError(f"Physical qubit {physical_qubit} not found in any controller")
