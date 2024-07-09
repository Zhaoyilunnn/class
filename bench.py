import random

from qiskit import QuantumCircuit, qasm2, qasm3, transpile
from qiskit.compiler import schedule
from qiskit.providers.fake_provider import Fake127QPulseV1
from qiskit.providers.fake_provider.fake_qasm_backend import json
from qiskit.visualization import plot_coupling_map, plot_error_map

from dqcmap import ControllerConf
from dqcmap.evaluator import Eval
from dqcmap.utils import get_cif_qubit_pairs

num_qubits = 10
length = 20
measure_qubits = [random.randint(0, num_qubits - 1) for _ in range(length)]
apply_qubits = [random.randint(0, num_qubits - 1) for _ in range(length)]
control_qubits = [random.randint(0, num_qubits - 1) for _ in range(length)]
target_qubits = [random.randint(0, num_qubits - 1) for _ in range(length)]

qc = QuantumCircuit(num_qubits, num_qubits)
for i in range(length):
    qc.measure(measure_qubits[i], measure_qubits[i])
    qc.h(apply_qubits[i]).c_if(measure_qubits[i], measure_qubits[i])
    if control_qubits[i] != target_qubits[i]:
        qc.cx(control_qubits[i], target_qubits[i])

# print(qasm2.dumps(qc))
print(qasm3.dumps(qc))
# print(qc.draw("text"))
cif_pairs = get_cif_qubit_pairs(qc)

dev = Fake127QPulseV1()
qc = transpile(qc, backend=dev)
# print(qasm2.dumps(qc))
# print(qasm3.dumps(qc))
# print(qc.draw("text"))
layout = qc.layout
# print(sorted(layout.initial_virtual_layout(filter_ancillas=True)._p2v.keys()))
print(layout.initial_virtual_layout(filter_ancillas=True))
# print(sorted(layout.final_virtual_layout(filter_ancillas=True)._p2v.keys()))
print(layout.final_virtual_layout(filter_ancillas=True))

sched = schedule(qc, backend=dev)
print(f"duration: {sched.duration}")

conf = dev.configuration()
cm = conf.coupling_map
print(cm)
# plot_coupling_map()

import matplotlib.pyplot as plt

plot_error_map(dev)
plt.show()
plt.savefig("temp.pdf")

conf = ControllerConf(127, 10)
evaluator = Eval(conf, cif_pairs)
total_latency = evaluator(qc, dev)
gate_latency = evaluator.gate_latency
ctrl_latency = evaluator.ctrl_latency
print(f"{gate_latency}\t{ctrl_latency}\t{total_latency}")
