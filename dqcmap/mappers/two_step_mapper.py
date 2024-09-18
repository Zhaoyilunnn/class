from typing import Dict, List, Set, Tuple, Optional
import random
import networkx as nx
from collections import defaultdict
import math

from dqcmap.basemapper import BaseMapper
from dqcmap.circuit_prop import CircProperty
from dqcmap.controller import ControllerConfig
from dqcmap.mappers.heuristic_graphpartition_mapper import HeuristicMapper
from dqcmap.mappers.intra_controller_optimizer import RandomIntraControllerMapper

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# TODO: Fix the issue that the initial mapping is not valid using a method similar to the sabre layout
class TwoStepMapper(BaseMapper):
    """
    A two-step qubit mapping algorithm that combines heuristic graph partitioning and intra-controller optimization.

    This mapper first uses a heuristic approach to partition qubits across controllers, 
    then runs random intra-controller mapping many times, 
    and choose the best one using a method similar to the sabre layout
    there is a cost function to evaluate the mapping quality. It aims to minimize cross-controller operations and swap gate overhead.
    

    Attributes:
        ctrl_conf (ControllerConfig): Configuration of the quantum device controllers.
        circ_prop (CircProperty): Properties of the quantum circuit to be mapped.
        ctrl_to_pq (Dict[int, List[int]]): Mapping of controllers to physical qubits.
        n_logical (int): Number of logical qubits in the circuit.
        n_controllers (int): Number of controllers in the quantum device.
        all_physical_qubits (Set[int]): Set of all physical qubit ids.
        graph (Dict[int, Set[int]]): Graph representation of two-qubit interactions in the circuit.
        coupling_map (Set[Tuple[int, int]]): Set of allowed qubit couplings in the device.
        cross_controller_edges (Dict[int, Set[int]]): Mapping of cross-controller edges.
        coupling_graph (nx.Graph): NetworkX graph representation of the coupling map.
        shortest_paths (Dict[Tuple[int, int], int]): Precomputed shortest paths between qubit pairs.
        heuristic_mapper (HeuristicMapper): Instance of the heuristic graph partitioning mapper.
        random_intra_mapper (RandomIntraControllerMapper): Instance of the random intra-controller optimizer.
        num_trials (int): Number of trials for the mapping algorithm.
        max_iterations (int): Maximum number of iterations for each trial.
        w_cross (float): Weight for cross-controller operations in the cost function.
        w_swap (float): Weight for swap gate overhead in the cost function.
    """
    def __init__(self, ctrl_conf: ControllerConfig, circ_prop: CircProperty, num_trials: int = 2, max_iterations: int = 50):
        super().__init__(ctrl_conf, circ_prop)
        self.ctrl_conf = self._ctrl_conf
        self.circ_prop = self._circ_prop
        self.ctrl_to_pq = self._ctrl_conf.ctrl_to_pq
        self.n_logical = self._circ_prop.num_qubits
        self.n_controllers = len(self.ctrl_to_pq)
        self.all_physical_qubits = set(pq for pqs in self.ctrl_to_pq.values() for pq in pqs)
        self.graph = self.build_two_qubit_graph()
        # Modify this line to convert a list to a set of tuples
        self.coupling_map = set(tuple(edge) for edge in self._ctrl_conf._cm)
        self.cross_controller_edges = self.identify_cross_controller_edges()
        self.coupling_graph = nx.Graph(self._ctrl_conf._cm)  # Here use the original list form.
        self.shortest_paths = self.precompute_shortest_paths()

        self.heuristic_mapper = HeuristicMapper(ctrl_conf, circ_prop)
        self.random_intra_mapper = RandomIntraControllerMapper(ctrl_conf, circ_prop)
        self.num_trials = num_trials
        self.max_iterations = max_iterations
        
        self.w_cross = 20.0  # Weight for cross-controller operations
        self.w_swap = 1.0   # Weight for swap gate overhead

    def build_two_qubit_graph(self) -> Dict[int, Set[int]]:
        graph = defaultdict(set)
        for q1, q2 in self.circ_prop.two_qubit_gates:
            graph[q1].add(q2)
            graph[q2].add(q1)
        return graph

    def identify_cross_controller_edges(self) -> Dict[int, Set[int]]:
        cross_edges = defaultdict(set)
        for edge in self.coupling_map:
            ctrl1 = self.get_controller(edge[0])
            ctrl2 = self.get_controller(edge[1])
            if ctrl1 != ctrl2:
                cross_edges[edge[0]].add(edge[1])
                cross_edges[edge[1]].add(edge[0])
        return cross_edges

    def precompute_shortest_paths(self) -> Dict[Tuple[int, int], int]:
        shortest_paths = {}
        for source in self.coupling_graph.nodes():
            paths = nx.single_source_shortest_path_length(self.coupling_graph, source)
            for target, length in paths.items():
                shortest_paths[(source, target)] = length
                shortest_paths[(target, source)] = length
        return shortest_paths

    def run(self) -> List[int]:
        initial_mapping = self.heuristic_mapper.run()
        candidate_mappings = []

        # Generate all random intra-mapper trials
        for _ in range(self.num_trials):
            candidate_mapping = self.random_intra_mapper.run(initial_mapping)
            candidate_mappings.append(candidate_mapping)

        # Run sabre_layout once with all candidate mappings
        best_mapping = self.sabre_layout(candidate_mappings)

        return best_mapping

    def sabre_layout(self, candidate_mappings: List[List[int]]) -> List[int]:
        global_best_mapping = None
        global_best_score = float('inf')

        for initial_mapping in candidate_mappings:
            if len(initial_mapping) != self.n_logical:
                raise ValueError(f"Initial mapping size ({len(initial_mapping)}) does not match the number of qubits in the circuit ({self.n_logical})")

            if len(set(initial_mapping)) != len(initial_mapping):
                logger.warning("Initial mapping contains duplicate qubits. Skipping this candidate.")
                continue

            layout = {i: initial_mapping[i] for i in range(self.n_logical)}
            
            dep_graph = self.build_dependency_graph()
            executed_gates = set()
            remaining_gates = set(tuple(gate) for gate in self.circ_prop.two_qubit_gates)

            iteration = 0
            no_progress_count = 0
            best_remaining_gates = len(remaining_gates)
            temperature = 1.0
            cooling_rate = 0.99
            
            while remaining_gates and iteration < self.max_iterations:
                front_layer = self.get_front_layer(dep_graph, executed_gates)

                if not front_layer:
                    executable_gates = [g for g in remaining_gates if self.is_executable(g, layout)]
                    if not executable_gates:
                        logger.warning("No executable gates found. Restarting with the initial mapping.")
                        layout = {i: initial_mapping[i] for i in range(self.n_logical)}
                        no_progress_count = 0
                        continue
                    front_layer = executable_gates[:1]

                executable_gates = [g for g in front_layer if self.is_executable(g, layout)]
                if executable_gates:
                    gate = min(executable_gates, key=lambda g: self.gate_cost(g, layout, dep_graph))
                    executed_gates.add(gate)
                    remaining_gates.remove(gate)
                else:
                    best_swap = self.find_best_swap(layout, temperature, dep_graph)
                    if best_swap is None:
                        logger.warning("No valid swap found. Restarting with the initial mapping.")
                        layout = {i: initial_mapping[i] for i in range(self.n_logical)}
                        no_progress_count = 0
                        continue
                    q1, q2 = best_swap
                    layout[q1], layout[q2] = layout[q2], layout[q1]
                
                iteration += 1
                temperature *= cooling_rate
                logger.debug(f"Iteration {iteration}: Remaining gates {len(remaining_gates)}")
                logger.debug(f"Front layer gates: {front_layer}")
                logger.debug(f"Current layout: {layout}")

                if len(remaining_gates) < best_remaining_gates:
                    best_remaining_gates = len(remaining_gates)
                    no_progress_count = 0
                else:
                    no_progress_count += 1
                
                if no_progress_count > 100:
                    logger.warning(f"No progress for 100 iterations. Restarting with the initial mapping.")
                    layout = {i: initial_mapping[i] for i in range(self.n_logical)}
                    no_progress_count = 0
                    continue

            if iteration == self.max_iterations:
                logger.warning(f"Warning: Reached maximum iterations ({self.max_iterations}) in sabre_layout for a candidate.")

            current_mapping = [layout[q] for q in range(self.n_logical)]
            current_score = self.evaluate_mapping(current_mapping)

            if current_score < global_best_score:
                global_best_score = current_score
                global_best_mapping = current_mapping

        if global_best_mapping is None:
            logger.warning("No valid mapping found across all candidates. Using RandomIntraControllerMapper result.")
            return self.random_intra_mapper.run(self.heuristic_mapper.run())

        return global_best_mapping


    def evaluate_mapping(self, mapping: List[int]) -> float:
        cross_controller_cost = self.calculate_cross_controller_cost(mapping)
        swap_cost = self.calculate_total_swap_cost(mapping)
        return self.w_cross * cross_controller_cost + self.w_swap * swap_cost

    def calculate_cross_controller_cost(self, mapping: List[int]) -> int:
        cost = 0
        for gate in self.circ_prop.two_qubit_gates:
            q1, q2 = gate
            p1, p2 = mapping[q1], mapping[q2]
            if self.get_controller(p1) != self.get_controller(p2):
                cost += 1
        return cost

    def calculate_total_swap_cost(self, mapping: List[int]) -> int:
        cost = 0
        for gate in self.circ_prop.two_qubit_gates:
            q1, q2 = gate
            p1, p2 = mapping[q1], mapping[q2]
            cost += self.shortest_paths[(p1, p2)]
        return cost

    def build_dependency_graph(self) -> nx.MultiDiGraph:
        dep_graph = nx.MultiDiGraph()
        gate_list = [tuple(gate) for gate in self.circ_prop.two_qubit_gates]
        
        # Add all gates as nodes
        dep_graph.add_nodes_from(gate_list)
        
        # Create a dictionary to keep track of the last gate applied to each qubit
        last_gate = {}
        
        for idx, gate in enumerate(gate_list):
            q1, q2 = gate
            
            # Add edges from the last gates that operated on q1 or q2
            if q1 in last_gate:
                dep_graph.add_edge(last_gate[q1], gate, qubit=q1)
            if q2 in last_gate:
                dep_graph.add_edge(last_gate[q2], gate, qubit=q2)
            
            # Update the last gate for both qubits
            last_gate[q1] = gate
            last_gate[q2] = gate
        
        return dep_graph

    def get_front_layer(self, dep_graph: nx.MultiDiGraph, executed_gates: Set[Tuple[int, int]]) -> List[Tuple[int, int]]:
        front_layer = []
        for gate in dep_graph.nodes():
            if gate not in executed_gates:
                predecessors = list(dep_graph.predecessors(gate))
                if all(pred in executed_gates for pred in predecessors):
                    front_layer.append(gate)
        return front_layer

    def is_executable(self, gate: Tuple[int, int], layout: Dict[int, int]) -> bool:
        p1, p2 = layout[gate[0]], layout[gate[1]]
        return (p1, p2) in self.coupling_map or (p2, p1) in self.coupling_map

    def gate_cost(self, gate: Tuple[int, int], layout: Dict[int, int], dep_graph: nx.MultiDiGraph) -> float:
        p1, p2 = layout[gate[0]], layout[gate[1]]
        distance_cost = self.shortest_paths[(p1, p2)]
        cross_controller_cost = 10 if self.get_controller(p1) != self.get_controller(p2) else 0
        
        # Consider the number of dependent qubits
        dependent_qubits = set()
        for _, _, data in dep_graph.out_edges(gate, data=True):
            dependent_qubits.add(data['qubit'])
        
        dependency_cost = len(dependent_qubits) * 2  # Adjust the weight as needed
        
        return distance_cost + cross_controller_cost + dependency_cost

    def find_best_swap(self, layout: Dict[int, int], temperature: float, dep_graph: nx.MultiDiGraph) -> Optional[Tuple[int, int]]:
        best_swap = None
        best_cost = float('inf')
        for q1 in layout.keys():
            p1 = layout[q1]
            for p2 in self.coupling_graph.neighbors(p1):
                q2_candidates = [q for q, p in layout.items() if p == p2]
                if q2_candidates:
                    q2 = q2_candidates[0]
                    cost = self.calculate_swap_cost(q1, q2, layout, dep_graph)
                    if cost < best_cost or random.random() < math.exp((best_cost - cost) / temperature):
                        best_cost = cost
                        best_swap = (q1, q2)
        return best_swap

    def calculate_swap_cost(self, q1: int, q2: int, layout: Dict[int, int], dep_graph: nx.MultiDiGraph) -> float:
        temp_layout = layout.copy()
        temp_layout[q1], temp_layout[q2] = temp_layout[q2], temp_layout[q1]
        return sum(self.gate_cost(tuple(gate), temp_layout, dep_graph) for gate in self.circ_prop.two_qubit_gates)

    def get_controller(self, physical_qubit: int) -> int:
        for ctrl, pqs in self.ctrl_to_pq.items():
            if physical_qubit in pqs:
                return ctrl
        raise ValueError(f"Physical qubit {physical_qubit} not found in any controller")
