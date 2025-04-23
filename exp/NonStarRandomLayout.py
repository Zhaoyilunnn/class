import random
from collections import defaultdict

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np


class RandomMappingEvaluator:
    """Class to generate and evaluate random mappings for comparison"""

    def __init__(self, controller_graph, cidq_sets, controller_capacities):
        """
        Initialize the evaluator with:
        - controller_graph: NetworkX graph representing controller network
        - cidq_sets: List of CIDQ sets, each a list of qubit indices
        - controller_capacities: Dict mapping controller IDs to their capacities
        """
        self.G = controller_graph
        self.L_D = cidq_sets
        self.capacities = controller_capacities
        self.num_qubits = max([max(cidq_set) for cidq_set in cidq_sets])

        # Pre-compute all-pairs shortest paths and distances
        self.distances = dict(
            nx.all_pairs_dijkstra_path_length(self.G, weight="weight")
        )

    def generate_random_mapping(self):
        """Generate a random logical-to-physical qubit mapping"""
        # Initialize empty mappings
        M_Q = {}  # Logical to physical
        M_C = {}  # Physical to controller
        current_loads = {c: 0 for c in self.capacities}

        # Create list of all logical qubits
        logical_qubits = list(range(1, self.num_qubits + 1))

        # Shuffle the qubits to randomize assignment
        random.shuffle(logical_qubits)

        # Assign each qubit to a random controller with available capacity
        for qubit in logical_qubits:
            # Get controllers with available capacity
            available_controllers = [
                c for c in self.capacities if current_loads[c] < self.capacities[c]
            ]

            if not available_controllers:
                raise ValueError("No controller has available capacity")

            # Randomly select a controller
            controller = random.choice(available_controllers)

            # Assign the qubit
            phys_qubit = f"Q{controller}_{current_loads[controller]}"
            M_Q[qubit] = phys_qubit
            M_C[phys_qubit] = controller
            current_loads[controller] += 1

        return M_Q, M_C, current_loads

    def calculate_total_communication_cost(self, M_Q, M_C):
        """Calculate total communication cost based on critical path model"""
        total_cost = 0

        # For each CIDQ set
        for cidq_set in self.L_D:
            if len(cidq_set) < 2:
                continue  # Skip if not enough qubits

            # In each CIDQ set, the first qubit is measured and the rest are targets
            measured_qubit = cidq_set[0]
            target_qubits = cidq_set[1:]

            # Find maximum communication cost between measured qubit and any target qubit
            max_path_cost = 0

            if measured_qubit in M_Q:
                c_m = M_C[M_Q[measured_qubit]]  # Controller for measured qubit

                for target_qubit in target_qubits:
                    if target_qubit not in M_Q:
                        continue

                    c_t = M_C[M_Q[target_qubit]]  # Controller for target qubit

                    # If different controllers, calculate communication cost
                    if c_m != c_t:
                        path_cost = self.distances[c_m][c_t]
                        max_path_cost = max(max_path_cost, path_cost)

            # Add max cost for this CIDQ set to total
            total_cost += max_path_cost

        return total_cost

    def run_multiple_trials(self, num_trials=100):
        """Run multiple trials of random mapping and calculate average cost"""
        costs = []

        for i in range(num_trials):
            M_Q, M_C, _ = self.generate_random_mapping()
            cost = self.calculate_total_communication_cost(M_Q, M_C)
            costs.append(cost)

        return costs


def run_comparison():
    """Compare random vs. optimized mappings for 12-qubit QFT"""
    # Create controller network (mesh topology)
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
    for i in range(1, 12):
        cidq_set = list(range(i, 13))
        cidq_sets.append(cidq_set)

    # Controller capacities
    capacities = {1: 3, 2: 3, 3: 3, 4: 3, 5: 3}

    # Create evaluator for random mappings
    evaluator = RandomMappingEvaluator(G, cidq_sets, capacities)

    # Run trials for random mapping
    num_trials = 1000
    random_costs = evaluator.run_multiple_trials(num_trials)

    # Calculate statistics
    avg_cost = sum(random_costs) / len(random_costs)
    min_cost = min(random_costs)
    max_cost = max(random_costs)

    print(f"Random Mapping Results ({num_trials} trials):")
    print(f"Average communication cost: {avg_cost:.2f}")
    print(f"Minimum communication cost: {min_cost}")
    print(f"Maximum communication cost: {max_cost}")

    # Create and run the optimizer for comparison
    from NonStarControllerCentricLayout import (  # Import your existing class
        NonStarCLASS,
    )

    optimizer = NonStarCLASS(G, cidq_sets, capacities)
    optimizer.verbose = False  # Disable detailed output
    M_Q, M_C = optimizer.run_optimization()
    optimized_cost = optimizer._calculate_total_communication_cost()

    print("\nOptimized Mapping Results:")
    print(f"Optimized communication cost: {optimized_cost}")
    print(
        f"Improvement over average random: {(avg_cost - optimized_cost) / avg_cost * 100:.2f}%"
    )

    # Plot the distribution of random costs vs optimized cost
    plt.figure(figsize=(10, 6))
    plt.hist(random_costs, bins=20, alpha=0.7, color="skyblue", label="Random Mappings")
    plt.axvline(
        x=optimized_cost,
        color="red",
        linestyle="--",
        linewidth=2,
        label=f"Optimized Cost: {optimized_cost}",
    )
    plt.axvline(
        x=avg_cost,
        color="green",
        linestyle="-",
        linewidth=2,
        label=f"Average Random Cost: {avg_cost:.2f}",
    )

    plt.xlabel("Communication Cost")
    plt.ylabel("Frequency")
    plt.title("Distribution of Communication Costs: Random vs. Optimized")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("cost_comparison.png")
    plt.show()


# If you want to use this standalone without importing NonStarCLASS
def standalone_random_evaluation():
    """Run only the random mapping evaluation without comparison"""
    # Create controller network (mesh topology)
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
    for i in range(1, 12):
        cidq_set = list(range(i, 13))
        cidq_sets.append(cidq_set)

    # Controller capacities
    capacities = {1: 3, 2: 3, 3: 3, 4: 3, 5: 3}

    # Create evaluator for random mappings
    evaluator = RandomMappingEvaluator(G, cidq_sets, capacities)

    # Run trials for random mapping
    num_trials = 1000
    random_costs = evaluator.run_multiple_trials(num_trials)

    # Calculate statistics
    avg_cost = sum(random_costs) / len(random_costs)
    min_cost = min(random_costs)
    max_cost = max(random_costs)

    print(f"Random Mapping Results ({num_trials} trials):")
    print(f"Average communication cost: {avg_cost:.2f}")
    print(f"Minimum communication cost: {min_cost}")
    print(f"Maximum communication cost: {max_cost}")

    # Plot the distribution of random costs
    plt.figure(figsize=(10, 6))
    plt.hist(random_costs, bins=20, alpha=0.7, color="skyblue")
    plt.axvline(
        x=avg_cost,
        color="red",
        linestyle="--",
        linewidth=2,
        label=f"Average Cost: {avg_cost:.2f}",
    )

    plt.xlabel("Communication Cost")
    plt.ylabel("Frequency")
    plt.title("Distribution of Communication Costs for Random Mappings")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("random_costs.png")
    plt.show()


if __name__ == "__main__":
    # If you have NonStarCLASS available
    run_comparison()

    # If you don't have NonStarCLASS available
    # standalone_random_evaluation()
