"""
Randomized benchmarking

Reference:
    https://qiskit-community.github.io/qiskit-experiments/manuals/verification/randomized_benchmarking
"""


import matplotlib.pyplot as plt
import numpy as np
import qiskit.circuit.library as circuits

# For simulation
from qiskit_aer import AerSimulator
from qiskit_experiments.framework import BatchExperiment, ParallelExperiment
from qiskit_experiments.library import InterleavedRB, StandardRB
from qiskit_ibm_runtime.fake_provider import FakePerth

backend = AerSimulator.from_backend(FakePerth())

# lengths = np.arange(1, 800, 200)
lengths = np.arange(1, 10, 2)
num_samples = 10
seed = 1010
qubits = [0]

# Run an RB experiment on qubit 0
exp1 = StandardRB(qubits, lengths, num_samples=num_samples, seed=seed)
expdata1 = exp1.run(backend).block_for_results()
results1 = expdata1.analysis_results()

circ_lst = exp1.circuits()

for i, c in enumerate(circ_lst):
    # print(c.draw("mpl"))
    c.draw("mpl")
    plt.savefig(f"c_{i}.pdf")
    plt.close()

# View result data
# print("Gate error ratio: %s" % expdata1.experiment.analysis.options.gate_error_ratio)
# # display(expdata1.figure(0))
# for result in results1:
#     print(result)
