import random
import time
from typing import List, Tuple, Dict
from collections import defaultdict

from dqcmap.basemapper import BaseMapper
from dqcmap.exceptions import DqcMapException


class KL_Mapper(BaseMapper):
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
        res = []
        start_time = time.time()
        time_limit = 4.0
        best_mapping = None
        best_score = float('inf')

        while time.time() - start_time < time_limit:
            current_mapping = self.generate_initial_mapping()
            current_score = self.evaluate_mapping(current_mapping)

            improved = True
            local_search_count = 0
            while improved and local_search_count < 5:
                improved = False
                for ctrl1 in range(self.n_controllers):
                    for ctrl2 in range(ctrl1 + 1, self.n_controllers):
                        new_mapping, new_score = self.kernighan_lin_pass(current_mapping, ctrl1, ctrl2)
                        if new_score < current_score:
                            current_mapping = new_mapping
                            current_score = new_score
                            improved = True
                if new_score >= current_score:
                    local_search_count += 1
                    local_mapping = self.local_search(current_mapping, depth=3, iterations=100)
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

    def generate_initial_mapping(self) -> List[int]:
        mapping = [-1] * self.n_logical
        available_pqs = {ctrl: list(pqs) for ctrl, pqs in self.ctrl_to_pq.items()}
        sorted_qubits = sorted(range(self.n_logical), key=lambda q: len(self.graph[q]), reverse=True)
        
        for q in sorted_qubits:
            if mapping[q] != -1:
                continue

            best_ctrl = None
            max_intra_pairs = -1
            
            for ctrl, pqs in available_pqs.items():
                if not pqs:
                    continue
                
                intra_pairs = sum(1 for neighbor in self.graph[q] if mapping[neighbor] != -1 and self.get_controller(mapping[neighbor]) == ctrl)
                
                if intra_pairs > max_intra_pairs:
                    max_intra_pairs = intra_pairs
                    best_ctrl = ctrl
            
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

    def kernighan_lin_pass(self, mapping: List[int], ctrl1: int, ctrl2: int) -> Tuple[List[int], int]:
        partition1 = [q for q in range(self.n_logical) if self.get_controller(mapping[q]) == ctrl1]
        partition2 = [q for q in range(self.n_logical) if self.get_controller(mapping[q]) == ctrl2]
        
        unmoved = set(partition1 + partition2)
        gains = []
        current_mapping = mapping.copy()
        
        while unmoved:
            best_gain = float('-inf')
            best_pair = None
            
            for a in partition1:
                if a not in unmoved:
                    continue
                for b in partition2:
                    if b not in unmoved:
                        continue
                    gain = self.calculate_gain(current_mapping, a, b)
                    if gain > best_gain:
                        best_gain = gain
                        best_pair = (a, b)
            
            if best_pair is None:
                break
            
            a, b = best_pair
            gains.append((best_gain, a, b))
            unmoved.remove(a)
            unmoved.remove(b)
            partition1.remove(a)
            partition2.remove(b)
            partition1.append(b)
            partition2.append(a)
            
            current_mapping[a], current_mapping[b] = current_mapping[b], current_mapping[a]
        
        max_cumulative_gain = 0
        max_i = 0
        cumulative_gain = 0
        for i, (gain, _, _) in enumerate(gains):
            cumulative_gain += gain
            if cumulative_gain > max_cumulative_gain:
                max_cumulative_gain = cumulative_gain
                max_i = i + 1
        
        if max_i > 0:
            new_mapping = mapping.copy()
            for _, a, b in gains[:max_i]:
                new_mapping[a], new_mapping[b] = new_mapping[b], new_mapping[a]
            return new_mapping, self.evaluate_mapping(new_mapping)
        
        return mapping, self.evaluate_mapping(mapping)

    def calculate_gain(self, mapping: List[int], a: int, b: int) -> int:
        ctrl_a = self.get_controller(mapping[a])
        ctrl_b = self.get_controller(mapping[b])
        
        gain = 0
        for neighbor in self.graph[a]:
            if self.get_controller(mapping[neighbor]) == ctrl_b:
                gain += 1
            elif self.get_controller(mapping[neighbor]) == ctrl_a:
                gain -= 1
        
        for neighbor in self.graph[b]:
            if self.get_controller(mapping[neighbor]) == ctrl_a:
                gain += 1
            elif self.get_controller(mapping[neighbor]) == ctrl_b:
                gain -= 1
        
        return gain

    def evaluate_mapping(self, mapping: List[int]) -> int:
        score = 0
        for q1, q2 in self.cif_pairs:
            if self.get_controller(mapping[q1]) != self.get_controller(mapping[q2]):
                score += 1
        return score

    def get_controller(self, physical_qubit: int) -> int:
        for ctrl, pqs in self.ctrl_to_pq.items():
            if physical_qubit in pqs:
                return ctrl
        raise ValueError(f"Physical qubit {physical_qubit} not found in any controller")