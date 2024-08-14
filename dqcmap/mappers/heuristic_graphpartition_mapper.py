import logging
from collections import defaultdict
from typing import List, Dict, Tuple
import random

from dqcmap.basemapper import BaseMapper
from dqcmap.exceptions import DqcMapException


logger = logging.getLogger(__name__)

class Heuristic_Mapper(BaseMapper):
    """ global calculate_gain, max(single move gain, swap gain)
        with the help of local_search,
        and optimize_mapping,
        and find_best_move,the most important method in this class
    """
    def __init__(self, ctrl_conf, circ_prop):
        super().__init__(ctrl_conf, circ_prop)
        self.ctrl_to_pq = self._ctrl_conf.ctrl_to_pq
        self.cif_pairs = self._circ_prop.cif_pairs
        self.n_logical = self._circ_prop.num_qubits
        self.n_controllers = len(self.ctrl_to_pq)
        self.all_physical_qubits = [pq for pqs in self.ctrl_to_pq.values() for pq in pqs]
        
        self.graph = defaultdict(list)
        for u, v in self.cif_pairs:
            self.graph[u].append(v)
            self.graph[v].append(u)

    def run(self) -> List[int]:
        logger.info("Starting the mapping process...")
        # print("Starting the mapping process...")
        res = []
        
        max_iterations = 10
        best_mapping = None
        best_score = float('inf')

        for i in range(max_iterations):
            logger.info(f"Iteration {i+1}/{max_iterations}")
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
                    logger.debug(f"Improved mapping found. Score: {current_score}")
                else:
                    local_search_count += 1
                    local_mapping = self.local_search(current_mapping, depth=3, iterations=1000)
                    local_score = self.evaluate_mapping(local_mapping)
                    if local_score < current_score:
                        current_mapping = local_mapping
                        current_score = local_score
                        improved = True
                        logger.debug(f"Local search improved mapping. Score: {current_score}")
                    else:
                        local_search_count += 1

            if current_score < best_score:
                best_mapping = current_mapping
                best_score = current_score
                logger.info(f"New best mapping found. Score: {best_score}")

        if best_mapping is None:
            raise DqcMapException("Failed to find a valid mapping")

        logger.info(f"Final mapping found. Score: {best_score}")
        
        # print(f"Final mapping found. Score: {best_score}")
        return best_mapping

    def local_search(self, mapping: List[int], depth: int = 3, iterations: int = 1000) -> List[int]:
        best_mapping = mapping.copy()
        best_score = self.evaluate_mapping(best_mapping)

        for _ in range(iterations):
            current_mapping = best_mapping.copy()
            current_score = best_score

            for _ in range(depth):
                q1, q2 = random.sample(range(self.n_logical), 2)
                current_mapping[q1], current_mapping[q2] = current_mapping[q2], current_mapping[q1]
                
                new_score = self.evaluate_mapping(current_mapping)
                if new_score < current_score:
                    current_score = new_score
                else:
                    current_mapping[q1], current_mapping[q2] = current_mapping[q2], current_mapping[q1]

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

        all_moves = []
        gains = []

        while unmoved:
            best_move = self.find_best_move(mapping, unmoved, ctrl_to_logical)
            if best_move is None:
                break

            qubit, new_pq, exchange_qubit = best_move
            gain = self.calculate_move_gain(mapping, qubit, new_pq, exchange_qubit)
            
            all_moves.append((qubit, mapping[qubit], new_pq, exchange_qubit))
            gains.append(gain)

            self.apply_move(mapping, qubit, new_pq, exchange_qubit, ctrl_to_logical)
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

    def find_best_move(self, mapping: List[int], unmoved: set, ctrl_to_logical: Dict[int, set]) -> Tuple[int, int, int]:
        best_gain = float('-inf')
        best_move = None

        for qubit in unmoved:
            current_ctrl = self.get_controller(mapping[qubit])
            for target_ctrl in range(self.n_controllers):
                if target_ctrl == current_ctrl:
                    continue

                available_pq = self.find_available_physical_qubit(target_ctrl, set(mapping))
                if available_pq is not None:
                    gain = self.calculate_move_gain(mapping, qubit, available_pq, None)
                    if gain > best_gain:
                        best_gain = gain
                        best_move = (qubit, available_pq, None)

                for other_qubit in ctrl_to_logical[target_ctrl]:
                    if other_qubit in unmoved:
                        exchange_gain = self.calculate_move_gain(mapping, qubit, mapping[other_qubit], other_qubit)
                        if exchange_gain > best_gain:
                            best_gain = exchange_gain
                            best_move = (qubit, mapping[other_qubit], other_qubit)

        return best_move

    def calculate_move_gain(self, mapping: List[int], qubit: int, new_pq: int, exchange_qubit: int) -> int:
        old_pq = mapping[qubit]
        old_ctrl = self.get_controller(old_pq)
        new_ctrl = self.get_controller(new_pq)
        
        gain = 0
        for neighbor in self.graph[qubit]:
            neighbor_ctrl = self.get_controller(mapping[neighbor])
            if neighbor_ctrl == new_ctrl:
                gain += 1
            elif neighbor_ctrl == old_ctrl:
                gain -= 1
        
        if exchange_qubit is not None:
            for neighbor in self.graph[exchange_qubit]:
                neighbor_ctrl = self.get_controller(mapping[neighbor])
                if neighbor_ctrl == old_ctrl:
                    if neighbor == qubit:
                        gain -= 1
                    else:
                        gain += 1
                elif neighbor_ctrl == new_ctrl:
                    gain -= 1
        
        return gain

    def apply_move(self, mapping: List[int], qubit: int, new_pq: int, exchange_qubit: int, ctrl_to_logical: Dict[int, set]):
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

    def find_available_physical_qubit(self, ctrl: int, used_pqs: set) -> int:
        available_pqs = set(self.ctrl_to_pq[ctrl]) - used_pqs
        return random.choice(list(available_pqs)) if available_pqs else None

    def generate_initial_mapping(self) -> List[int]:
        mapping = [-1] * self.n_logical
        available_pqs = {ctrl: list(pqs) for ctrl, pqs in self.ctrl_to_pq.items()}
        sorted_qubits = sorted(range(self.n_logical), key=lambda q: len(self.graph[q]), reverse=True)
        
        for q in sorted_qubits:
            if mapping[q] != -1:
                continue

            best_ctrl = max(
                (ctrl for ctrl, pqs in available_pqs.items() if pqs),
                key=lambda ctrl: sum(1 for neighbor in self.graph[q] if mapping[neighbor] != -1 and self.get_controller(mapping[neighbor]) == ctrl),
                default=None
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
        return sum(self.get_controller(mapping[q1]) != self.get_controller(mapping[q2]) for q1, q2 in self.cif_pairs)

    def get_controller(self, physical_qubit: int) -> int:
        for ctrl, pqs in self.ctrl_to_pq.items():
            if physical_qubit in pqs:
                return ctrl
        raise ValueError(f"Physical qubit {physical_qubit} not found in any controller")