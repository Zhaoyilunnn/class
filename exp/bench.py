import argparse
import os
import random
import time

from qiskit import QuantumCircuit, qasm2, qasm3, transpile
from qiskit.compiler import schedule
from qiskit.providers.fake_provider import Fake127QPulseV1
from qiskit.providers.fake_provider.fake_qasm_backend import json
from qiskit.visualization import plot_coupling_map, plot_error_map

from dqcmap import ControllerConf
from dqcmap.evaluator import Eval
from dqcmap.utils import get_cif_qubit_pairs, get_synthetic_dqc


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", default=10, help="Number of qubits")
    parser.add_argument(
        "--p",
        default=0.5,
        type=float,
        help="Probability of generating conditional gates",
    )

    return parser.parse_args()


def get_benchmark(
    num_qubits: int,
    depth: int,
    cond_ratio: float,
    use_qiskit: bool,
    idx: int,
    qc_type: str = "random",
):
    ratio = int(cond_ratio * 100)  # just for file naming
    gen_type = 1 if use_qiskit else 0
    filename = f"random_{num_qubits}_{depth}_{ratio}_type_{gen_type}_{idx}.qasm"
    filepath = os.path.join("benchmarks", filename)
    qc = qasm3.load(filepath)
    return qc


def main():
    args = get_args()
    num_qubits = args.n
    depth = num_qubits

    timestamp = int(time.time())
    res = open(f"{timestamp}_res.txt", "w")
    res.write("gate_latency\tctrl_latency\tinner\tinter\ttotal_latency\n")

    for idx in range(10):
        # https://github.com/Zhaoyilunnn/dqc-map/issues/3
        # due to the above issue, currently we do not rely on qasm files
        # instead, we generate circuits dynamically
        # reproducibility is guaranteed by setting fixed random seed
        # qc = get_benchmark(num_qubits, depth, args.p, False, idx)

        qc = get_synthetic_dqc(
            num_qubits, depth, cond_ratio=args.p, use_qiskit=False, seed=1900 + idx
        )

        # print(qasm2.dumps(qc))
        # print(qasm3.dumps(qc))
        # print(qc.draw("text"))
        cif_pairs = get_cif_qubit_pairs(qc)

        dev = Fake127QPulseV1()
        qc = transpile(qc, backend=dev, layout_method="dummy_layout")
        # qc = transpile(qc, backend=dev)
        # print(qasm2.dumps(qc))
        # print(qasm3.dumps(qc))
        # print(qc.draw("text"))
        layout = qc.layout
        # print(sorted(layout.initial_virtual_layout(filter_ancillas=True)._p2v.keys()))
        # print(layout.initial_virtual_layout(filter_ancillas=True))
        # print(sorted(layout.final_virtual_layout(filter_ancillas=True)._p2v.keys()))
        # print(layout.final_virtual_layout(filter_ancillas=True))

        sched = schedule(qc, backend=dev)
        # print(f"duration: {sched.duration}")

        # import matplotlib.pyplot as plt

        # plot_error_map(dev)
        # plt.show()
        # plt.savefig("temp.pdf")

        conf = ControllerConf(127, 10)
        evaluator = Eval(conf, cif_pairs)
        total_latency = evaluator(qc, dev)
        gate_latency = evaluator.gate_latency
        ctrl_latency = evaluator.ctrl_latency
        inner = evaluator.inner_latency
        inter = evaluator.inter_latency
        res.write(
            f"{gate_latency}\t{ctrl_latency}\t{inner}\t{inter}\t{total_latency}\n"
        )

    res.close()


if __name__ == "__main__":
    main()
