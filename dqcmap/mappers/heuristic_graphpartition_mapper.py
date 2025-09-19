import random
from collections import defaultdict
from typing import Dict, List, Set, Tuple

from dqcmap.basemapper import BaseMapper
from dqcmap.circuit_prop import CircProperty
from dqcmap.controller import ControllerConfig
from dqcmap.exceptions import DqcMapException


class HeuristicMapper(BaseMapper):
    """
    global calculate_gain, max(single move gain, swap gain)
        with the help of local_search,
        and optimize_mapping,
        and find_best_move,the most important method in this class
    this version is Accelerated
    Introduce a caching mechanism in the find_best_move and calculate_move_gain methods to reduce redundant calculations.
    """

    def __init__(self, ctrl_conf: ControllerConfig, circ_prop: CircProperty):
        super().__init__(ctrl_conf, circ_prop)
        self.ctrl_to_pq = self._ctrl_conf.ctrl_to_pq
        self.cif_pairs = self._circ_prop.cif_pairs
        self.n_logical = self._circ_prop.num_qubits
        self.n_controllers = len(self.ctrl_to_pq)
        self.all_physical_qubits = [
            pq for pqs in self.ctrl_to_pq.values() for pq in pqs
        ]

        self.graph = defaultdict(list)
        for u, v in self.cif_pairs:
            self.graph[u].append(v)
            self.graph[v].append(u)

        self.move_gain_cache = {}
        self.swap_gain_cache = {}

    def run(self) -> List[int]:
        max_iterations = 10
        best_mapping = None
        best_score = float("inf")

        for _ in range(max_iterations):
            current_mapping = self.generate_initial_mapping()
            current_score = self.evaluate_mapping(current_mapping)

            improved = True
            local_search_count = 0
            while improved and local_search_count < 5:
                improved = False
                new_mapping = self.optimize_mapping(current_mapping)
                new_score = self.evaluate_mapping(new_mapping)

                if new_score < current_score:
                    current_mapping = new_mapping
                    current_score = new_score
                    improved = True
                    local_search_count = 0
                else:
                    local_search_count += 1
                    local_mapping = self.local_search(
                        current_mapping, depth=3, iterations=1000
                    )
                    local_score = self.evaluate_mapping(local_mapping)
                    if local_score < current_score:
                        current_mapping = local_mapping
                        current_score = local_score
                        improved = True
                    else:
                        local_search_count += 1

            if current_score < best_score:
                best_mapping = current_mapping
                best_score = current_score

        if best_mapping is None:
            raise DqcMapException("Failed to find a valid mapping")

        return best_mapping

    def local_search(
        self, mapping: List[int], depth: int = 3, iterations: int = 1000
    ) -> List[int]:
        best_mapping = mapping.copy()
        best_score = self.evaluate_mapping(best_mapping)

        for _ in range(iterations):
            current_mapping = best_mapping.copy()
            current_score = best_score

            for _ in range(depth):
                q1, q2 = random.sample(range(self.n_logical), 2)
                current_mapping[q1], current_mapping[q2] = (
                    current_mapping[q2],
                    current_mapping[q1],
                )

                new_score = self.evaluate_mapping(current_mapping)
                if new_score < current_score:
                    current_score = new_score
                else:
                    current_mapping[q1], current_mapping[q2] = (
                        current_mapping[q2],
                        current_mapping[q1],
                    )

            if current_score < best_score:
                best_mapping = current_mapping
                best_score = current_score

        return best_mapping

    def optimize_mapping(self, initial_mapping: List[int]) -> List[int]:
        mapping = initial_mapping.copy()
        unmoved = set(range(self.n_logical))
        ctrl_to_logical = defaultdict(set)
        for q, pq in enumerate(mapping):
            ctrl_to_logical[self.get_controller(pq)].add(q)

        self.initialize_gain_caches(mapping, unmoved, ctrl_to_logical)

        all_moves = []
        gains = []

        while unmoved:
            best_move = self.find_best_move(mapping, unmoved, ctrl_to_logical)
            if best_move is None:
                break

            qubit, new_pq, exchange_qubit = best_move
            gain = self.calculate_total_gain(mapping, qubit, new_pq, exchange_qubit)

            all_moves.append((qubit, mapping[qubit], new_pq, exchange_qubit))
            gains.append(gain)

            self.apply_move(mapping, qubit, new_pq, exchange_qubit, ctrl_to_logical)
            self.update_gain_caches(
                mapping, qubit, exchange_qubit, unmoved, ctrl_to_logical
            )
            unmoved.remove(qubit)
            if exchange_qubit is not None:
                unmoved.remove(exchange_qubit)

        max_cumulative_gain = 0
        max_i = 0
        cumulative_gain = 0
        for i, gain in enumerate(gains):
            cumulative_gain += gain
            if cumulative_gain > max_cumulative_gain:
                max_cumulative_gain = cumulative_gain
                max_i = i + 1

        if max_i > 0:
            best_mapping = initial_mapping.copy()
            for i in range(max_i):
                qubit, old_pq, new_pq, exchange_qubit = all_moves[i]
                best_mapping[qubit] = new_pq
                if exchange_qubit is not None:
                    best_mapping[exchange_qubit] = old_pq

            return best_mapping
        else:
            return initial_mapping

    def initialize_gain_caches(
        self,
        mapping: List[int],
        unmoved: Set[int],
        ctrl_to_logical: Dict[int, Set[int]],
    ):
        for qubit in unmoved:
            current_ctrl = self.get_controller(mapping[qubit])
            for target_ctrl in range(self.n_controllers):
                if target_ctrl != current_ctrl:
                    self.move_gain_cache[(qubit, target_ctrl)] = (
                        self.calculate_move_gain(mapping, qubit, target_ctrl)
                    )
                    for other_qubit in ctrl_to_logical[target_ctrl]:
                        if other_qubit in unmoved:
                            self.swap_gain_cache[(qubit, other_qubit)] = (
                                self.calculate_swap_gain(mapping, qubit, other_qubit)
                            )

    def update_gain_caches(
        self,
        mapping: List[int],
        moved_qubit: int,
        exchange_qubit: int,
        unmoved: Set[int],
        ctrl_to_logical: Dict[int, Set[int]],
    ):
        affected_qubits = set(self.graph[moved_qubit])
        if exchange_qubit is not None:
            affected_qubits.update(self.graph[exchange_qubit])
        affected_qubits &= unmoved

        for qubit in affected_qubits:
            current_ctrl = self.get_controller(mapping[qubit])
            for target_ctrl in range(self.n_controllers):
                if target_ctrl != current_ctrl:
                    self.move_gain_cache[(qubit, target_ctrl)] = (
                        self.calculate_move_gain(mapping, qubit, target_ctrl)
                    )
                    for other_qubit in ctrl_to_logical[target_ctrl]:
                        if other_qubit in unmoved:
                            self.swap_gain_cache[(qubit, other_qubit)] = (
                                self.calculate_swap_gain(mapping, qubit, other_qubit)
                            )
                            self.swap_gain_cache[(other_qubit, qubit)] = (
                                self.swap_gain_cache[(qubit, other_qubit)]
                            )

    def find_best_move(
        self,
        mapping: List[int],
        unmoved: Set[int],
        ctrl_to_logical: Dict[int, Set[int]],
    ) -> Tuple[int, int, int]:
        best_move_gain = float("-inf")
        best_move = None
        best_swap_gain = float("-inf")
        best_swap = None

        for qubit in unmoved:
            current_ctrl = self.get_controller(mapping[qubit])

            target_ctrl, move_gain = max(
                (
                    (ctrl, self.move_gain_cache[(qubit, ctrl)])
                    for ctrl in range(self.n_controllers)
                    if ctrl != current_ctrl
                ),
                key=lambda x: x[1],
            )

            if move_gain > best_move_gain:
                available_pq = self.find_available_physical_qubit(
                    target_ctrl, set(mapping)
                )
                if available_pq is not None:
                    best_move_gain = move_gain
                    best_move = (qubit, available_pq, None)

            best_qubit_swap = max(
                (
                    (other_qubit, self.swap_gain_cache[(qubit, other_qubit)])
                    for ctrl in range(self.n_controllers)
                    for other_qubit in ctrl_to_logical[ctrl]
                    if other_qubit in unmoved and ctrl != current_ctrl
                ),
                key=lambda x: x[1],
                default=(None, float("-inf")),
            )

            if best_qubit_swap[1] > best_swap_gain:
                best_swap_gain = best_qubit_swap[1]
                best_swap = (qubit, mapping[best_qubit_swap[0]], best_qubit_swap[0])

        return best_move if best_move_gain >= best_swap_gain else best_swap

    def calculate_move_gain(self, mapping: List[int], qubit: int, new_ctrl: int) -> int:
        old_ctrl = self.get_controller(mapping[qubit])

        gain = 0
        for neighbor in self.graph[qubit]:
            neighbor_ctrl = self.get_controller(mapping[neighbor])
            if neighbor_ctrl == new_ctrl:
                gain += 1
            elif neighbor_ctrl == old_ctrl:
                gain -= 1

        return gain

    def calculate_swap_gain(self, mapping: List[int], qubit1: int, qubit2: int) -> int:
        ctrl1 = self.get_controller(mapping[qubit1])
        ctrl2 = self.get_controller(mapping[qubit2])

        gain = 0

        for neighbor in self.graph[qubit1]:
            neighbor_ctrl = self.get_controller(mapping[neighbor])
            if neighbor_ctrl == ctrl2:
                gain += 1
            elif neighbor_ctrl == ctrl1:
                gain -= 1

        for neighbor in self.graph[qubit2]:
            neighbor_ctrl = self.get_controller(mapping[neighbor])
            if neighbor_ctrl == ctrl1:
                gain += 1
            elif neighbor_ctrl == ctrl2:
                gain -= 1

        for neighbor in self.graph[qubit1]:
            if neighbor == qubit2:
                gain -= 2

        return gain

    def calculate_total_gain(
        self, mapping: List[int], qubit: int, new_pq: int, exchange_qubit: int
    ) -> int:
        new_ctrl = self.get_controller(new_pq)
        if exchange_qubit is None:
            return self.move_gain_cache[(qubit, new_ctrl)]
        else:
            return self.swap_gain_cache[(qubit, exchange_qubit)]

    def apply_move(
        self,
        mapping: List[int],
        qubit: int,
        new_pq: int,
        exchange_qubit: int,
        ctrl_to_logical: Dict[int, Set[int]],
    ):
        old_pq = mapping[qubit]
        old_ctrl = self.get_controller(old_pq)
        new_ctrl = self.get_controller(new_pq)

        mapping[qubit] = new_pq
        ctrl_to_logical[old_ctrl].remove(qubit)
        ctrl_to_logical[new_ctrl].add(qubit)

        if exchange_qubit is not None:
            mapping[exchange_qubit] = old_pq
            ctrl_to_logical[new_ctrl].remove(exchange_qubit)
            ctrl_to_logical[old_ctrl].add(exchange_qubit)

    def find_available_physical_qubit(self, ctrl: int, used_pqs: Set[int]) -> int:
        available_pqs = set(self.ctrl_to_pq[ctrl]) - used_pqs
        return random.choice(list(available_pqs)) if available_pqs else None

    def generate_initial_mapping(self) -> List[int]:
        mapping = [-1] * self.n_logical
        available_pqs = {ctrl: list(pqs) for ctrl, pqs in self.ctrl_to_pq.items()}
        sorted_qubits = sorted(
            range(self.n_logical), key=lambda q: len(self.graph[q]), reverse=True
        )

        for q in sorted_qubits:
            if mapping[q] != -1:
                continue

            best_ctrl = max(
                (ctrl for ctrl, pqs in available_pqs.items() if pqs),
                key=lambda ctrl: sum(
                    1
                    for neighbor in self.graph[q]
                    if mapping[neighbor] != -1
                    and self.get_controller(mapping[neighbor]) == ctrl
                ),
                default=None,
            )

            if best_ctrl is not None:
                pq = random.choice(available_pqs[best_ctrl])
                available_pqs[best_ctrl].remove(pq)
                mapping[q] = pq

                for neighbor in self.graph[q]:
                    if mapping[neighbor] == -1 and available_pqs[best_ctrl]:
                        pq = available_pqs[best_ctrl].pop()
                        mapping[neighbor] = pq
            else:
                for ctrl, pqs in available_pqs.items():
                    if pqs:
                        pq = random.choice(pqs)
                        available_pqs[ctrl].remove(pq)
                        mapping[q] = pq
                        break

        return mapping

    def evaluate_mapping(self, mapping: List[int]) -> int:
        return sum(
            self.get_controller(mapping[q1]) != self.get_controller(mapping[q2])
            for q1, q2 in self.cif_pairs
        )

    def get_controller(self, physical_qubit: int) -> int:
        for ctrl, pqs in self.ctrl_to_pq.items():
            if physical_qubit in pqs:
                return ctrl
        raise ValueError(f"Physical qubit {physical_qubit} not found in any controller")
