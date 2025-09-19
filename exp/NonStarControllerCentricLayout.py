from collections import defaultdict

import matplotlib.pyplot as plt
import networkx as nx


class NonStarCLASS:
    def __init__(self, controller_graph, cidq_sets, controller_capacities):
        """
        Initialize the optimizer with:
        - controller_graph: NetworkX graph representing controller network
        - cidq_sets: List of CIDQ sets, each a list of qubit indices where the first is measured
                     and the rest are targets
        - controller_capacities: Dict mapping controller IDs to their capacities
        """
        self.G = controller_graph
        self.L_D = cidq_sets
        self.capacities = controller_capacities
        self.current_loads = {c: 0 for c in controller_capacities}
        self.M_Q = {}  # Logical to physical qubit mapping
        self.M_C = {}  # Physical qubit to controller mapping
        self.verbose = False

        # Pre-compute all-pairs shortest paths and distances
        self.shortest_paths = dict(nx.all_pairs_dijkstra_path(self.G, weight="weight"))
        self.distances = dict(
            nx.all_pairs_dijkstra_path_length(self.G, weight="weight")
        )

    def run_optimization(self):
        """Execute the two-stage optimization algorithm"""
        # Stage 1: Initialize mapping with topology awareness
        self._initialize_mapping()

        # Stage 2: Iterative improvement
        self._iterative_improvement()

        return self.M_Q, self.M_C

    def _initialize_mapping(self):
        """Topology-aware initial placement (Stage 1)"""
        # First identify all unique qubits from CIDQ sets
        all_qubits = set()
        for cidq_set in self.L_D:
            all_qubits.update(cidq_set)

        # Build dependency graph and calculate qubit importance
        qubit_dependencies = defaultdict(set)
        qubit_importance = defaultdict(int)

        # In each CIDQ set, the first qubit is measured and the rest are targets
        for cidq_set in self.L_D:
            if len(cidq_set) < 2:
                continue  # Skip if there aren't enough qubits

            measured_qubit = cidq_set[0]
            target_qubits = cidq_set[1:]

            # Measured qubits are more critical as they affect multiple targets
            qubit_importance[measured_qubit] += len(target_qubits) * 2

            for target_qubit in target_qubits:
                qubit_dependencies[measured_qubit].add(target_qubit)
                qubit_dependencies[target_qubit].add(measured_qubit)
                qubit_importance[target_qubit] += 1

        # Sort qubits by importance (descending)
        sorted_qubits = sorted(
            all_qubits, key=lambda q: qubit_importance[q], reverse=True
        )

        # Process qubits in order of importance
        for q_i in sorted_qubits:
            # Skip if already assigned
            if q_i in self.M_Q:
                continue

            # Calculate controller costs based on critical path model
            controller_costs = defaultdict(float)

            # Check if any dependent qubits are already assigned
            neighbors_assigned = False
            for q_j in qubit_dependencies[q_i]:
                if q_j in self.M_Q:
                    neighbors_assigned = True
                    q_j_controller = self.M_C[self.M_Q[q_j]]

                    # Calculate costs for each potential controller
                    for c_k in self.capacities:
                        if self.current_loads[c_k] < self.capacities[c_k]:
                            communication_cost = self.distances[q_j_controller][c_k]
                            controller_costs[c_k] += communication_cost

            # Select best controller
            if neighbors_assigned:
                # Choose controller with minimum communication cost
                best_controller = min(
                    [
                        c
                        for c in self.capacities
                        if self.current_loads[c] < self.capacities[c]
                    ],
                    key=lambda c: controller_costs.get(c, float("inf")),
                )
            else:
                # Choose central controller with capacity
                best_controller = self._select_network_central_controller()

            # Assign qubit to controller
            phys_qubit_id = f"Q{best_controller}_{self.current_loads[best_controller]}"
            self.M_Q[q_i] = phys_qubit_id
            self.M_C[phys_qubit_id] = best_controller
            self.current_loads[best_controller] += 1

    def _select_network_central_controller(self):
        """Select a central controller with available capacity"""
        # Filter controllers with available capacity
        available_controllers = [
            c for c in self.capacities if self.current_loads[c] < self.capacities[c]
        ]

        if not available_controllers:
            raise ValueError("No controller has available capacity")

        # Calculate closeness centrality
        closeness_values = {}
        for c in available_controllers:
            total_distance = sum(self.distances[c].values())
            if total_distance > 0:
                closeness_values[c] = (len(self.G.nodes) - 1) / total_distance
            else:
                closeness_values[c] = 0

        # Find controller with highest centrality
        best_controller = max(available_controllers, key=lambda c: closeness_values[c])

        return best_controller

    def _iterative_improvement(self):
        """Improve the mapping through iterative movement (Stage 2)"""
        best_score = self._calculate_total_communication_cost()
        improved = True

        while improved:
            improved = False

            # For each controller
            for c_i in self.capacities:
                # Get qubits assigned to this controller
                c_i_qubits = [
                    q for q, phys_q in self.M_Q.items() if self.M_C[phys_q] == c_i
                ]

                # For each qubit in this controller
                for q_i in c_i_qubits:
                    best_move = None
                    best_move_gain = 0

                    # Consider all other controllers with capacity
                    for c_j in self.capacities:
                        if (
                            c_j != c_i
                            and self.current_loads[c_j] < self.capacities[c_j]
                        ):
                            # Calculate gain from moving q_i from c_i to c_j
                            current_cost = self._calculate_total_communication_cost()

                            # Temporarily move qubit
                            old_phys_qubit = self.M_Q[q_i]
                            new_phys_qubit = f"Q{c_j}_{self.current_loads[c_j]}"
                            old_controller = self.M_C[old_phys_qubit]

                            self.M_C.pop(old_phys_qubit)
                            self.M_Q[q_i] = new_phys_qubit
                            self.M_C[new_phys_qubit] = c_j
                            self.current_loads[old_controller] -= 1
                            self.current_loads[c_j] += 1

                            # Calculate new cost
                            new_cost = self._calculate_total_communication_cost()
                            gain = current_cost - new_cost

                            # Restore original state
                            self.M_C.pop(new_phys_qubit)
                            self.M_Q[q_i] = old_phys_qubit
                            self.M_C[old_phys_qubit] = old_controller
                            self.current_loads[c_j] -= 1
                            self.current_loads[old_controller] += 1

                            if gain > best_move_gain:
                                best_move_gain = gain
                                best_move = (q_i, c_j)

                    # Apply the best move if it improves the solution
                    if best_move and best_move_gain > 0:
                        q_to_move, target_controller = best_move

                        # Update mappings
                        old_phys_qubit = self.M_Q[q_to_move]
                        old_controller = self.M_C[old_phys_qubit]
                        new_phys_qubit = f"Q{target_controller}_{self.current_loads[target_controller]}"

                        self.M_C.pop(old_phys_qubit)
                        self.M_Q[q_to_move] = new_phys_qubit
                        self.M_C[new_phys_qubit] = target_controller

                        self.current_loads[old_controller] -= 1
                        self.current_loads[target_controller] += 1

                        improved = True
                        break

                if improved:
                    break

            # Calculate new total cost
            new_score = self._calculate_total_communication_cost()
            if new_score < best_score:
                best_score = new_score
            else:
                # No improvement was found or applied
                improved = False

    def _calculate_total_communication_cost(self):
        """Calculate total communication cost based on critical path model"""
        total_cost = 0

        # For each CIDQ set
        for i, cidq_set in enumerate(self.L_D):
            if len(cidq_set) < 2:
                continue  # Skip if not enough qubits

            # In each CIDQ set, the first qubit is measured and the rest are targets
            measured_qubit = cidq_set[0]
            target_qubits = cidq_set[1:]

            # Find maximum communication cost between measured qubit and any target qubit
            max_path_cost = 0
            critical_path = None

            if measured_qubit in self.M_Q:
                c_m = self.M_C[
                    self.M_Q[measured_qubit]
                ]  # Controller for measured qubit

                for target_qubit in target_qubits:
                    if target_qubit not in self.M_Q:
                        continue

                    c_t = self.M_C[
                        self.M_Q[target_qubit]
                    ]  # Controller for target qubit

                    # If different controllers, calculate communication cost
                    if c_m != c_t:
                        path_cost = self.distances[c_m][c_t]
                        if path_cost > max_path_cost:
                            max_path_cost = path_cost
                            critical_path = (
                                measured_qubit,
                                c_m,
                                target_qubit,
                                c_t,
                                path_cost,
                            )

            # Add max cost for this CIDQ set to total
            total_cost += max_path_cost

            # Optionally print detailed information about each CIDQ set
            if (
                self.verbose and i < 5
            ):  # Limit printing to first few sets to avoid clutter
                if critical_path:
                    q_m, c_m, q_t, c_t, cost = critical_path
                    print(
                        f"CIDQ Set {i + 1}: Critical path from q{q_m}(C{c_m}) to q{q_t}(C{c_t}) with cost {cost}"
                    )
                else:
                    print(
                        f"CIDQ Set {i + 1}: No communication needed (all qubits on same controller or not mapped)"
                    )

        return total_cost

    def visualize_solution(self):
        """Visualize the network and qubit mapping solution"""
        plt.figure(figsize=(12, 8))

        # Create position layout for visualization
        pos = nx.spring_layout(self.G, seed=42)

        # Draw network
        nx.draw(
            self.G,
            pos,
            with_labels=True,
            node_color="skyblue",
            node_size=800,
            font_size=12,
            font_weight="bold",
        )

        # Draw edge weights
        edge_labels = {(u, v): d["weight"] for u, v, d in self.G.edges(data=True)}
        nx.draw_networkx_edge_labels(self.G, pos, edge_labels=edge_labels)

        # Show qubit assignments
        controller_qubits = defaultdict(list)
        for q, phys_q in self.M_Q.items():
            c = self.M_C[phys_q]
            controller_qubits[c].append(f"q{q}")

        for c, qubits in controller_qubits.items():
            qubit_str = ", ".join(qubits)
            plt.annotate(
                f"Qubits: {qubit_str}",
                xy=pos[c],
                xytext=(20, 20),
                textcoords="offset points",
                bbox=dict(boxstyle="round,pad=0.3", fc="yellow", alpha=0.8),
            )

        # Show CIDQ sets
        plt.figtext(
            0.5,
            0.01,
            f"CIDQ Sets: {len(self.L_D)} sets",
            ha="center",
            fontsize=10,
            bbox=dict(boxstyle="round,pad=0.3", fc="lightgray", alpha=0.8),
        )

        plt.title("Controller Network with Qubit Mapping")
        plt.tight_layout()
        plt.show()


def run_example():
    """Run the optimization for a 12-qubit dynamic QFT circuit"""
    # Create controller network
    G = nx.Graph()
    for i in range(1, 6):
        G.add_node(i)

    edges_with_weights = [
        (1, 2, 4),
        (1, 3, 2),
        (1, 4, 2),
        (2, 3, 3),
        (2, 5, 3),
        (3, 4, 2),
        (3, 5, 1),
        (4, 5, 2),
    ]
    G.add_weighted_edges_from(edges_with_weights)

    # Define CIDQ sets for 12-qubit dynamic QFT
    cidq_sets = []
    for i in range(1, 12):  # We have 11 CIDQ sets for 12 qubits
        cidq_set = list(
            range(i, 13)
        )  # Python uses 0-indexing, so we add 1 to each index
        cidq_sets.append(cidq_set)

    # Print the CIDQ sets to verify
    print("CIDQ Sets for 12-qubit dynamic QFT:")
    for i, cidq_set in enumerate(cidq_sets):
        print(f"D_{i + 1} = {cidq_set}")

    # Controller capacities
    capacities = {1: 3, 2: 3, 3: 3, 4: 3, 5: 3}

    # Create and run the optimizer
    optimizer = NonStarCLASS(G, cidq_sets, capacities)
    optimizer.verbose = False  # Enable detailed output
    M_Q, M_C = optimizer.run_optimization()

    print("\nSolution:")
    print("Logical-Physical Mapping (M_Q):", M_Q)
    print("Physical-Controller Mapping (M_C):", M_C)
    print("Final controller loads:", optimizer.current_loads)
    print("Total communication cost:", optimizer._calculate_total_communication_cost())

    # Analyze CIDQ set distribution
    print("\nCIDQ Set Distribution:")
    for i, cidq_set in enumerate(cidq_sets):
        measured_qubit = cidq_set[0]
        target_qubits = cidq_set[1:]

        if measured_qubit in M_Q:
            measured_controller = M_C[M_Q[measured_qubit]]
            target_controllers = {M_C[M_Q[q]] for q in target_qubits if q in M_Q}

            print(
                f"D_{i + 1}: Measured q{measured_qubit} on controller {measured_controller}, "
                f"targets on controllers {target_controllers}"
            )

            # Identify critical paths
            max_cost = 0
            critical_target = None
            for target in target_qubits:
                if target in M_Q:
                    target_controller = M_C[M_Q[target]]
                    if target_controller != measured_controller:
                        cost = optimizer.distances[measured_controller][
                            target_controller
                        ]
                        if cost > max_cost:
                            max_cost = cost
                            critical_target = target

            if critical_target:
                target_controller = M_C[M_Q[critical_target]]
                print(
                    f"  Critical path: {measured_controller} → {target_controller} "
                    f"with cost {optimizer.distances[measured_controller][target_controller]}"
                )
            else:
                print(
                    "  No critical path (all targets on same controller as measured qubit)"
                )
        else:
            print(f"D_{i + 1}: Measured qubit q{measured_qubit} not mapped")

    # Visualize the solution
    optimizer.visualize_solution()


if __name__ == "__main__":
    run_example()
