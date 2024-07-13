import argparse
import logging
import os
import random
import time
from typing import List

import numpy as np
from qiskit import QuantumCircuit, qasm2, qasm3, transpile
from qiskit.compiler import schedule
from qiskit.providers.fake_provider import Fake127QPulseV1
from qiskit.providers.fake_provider.fake_qasm_backend import json
from qiskit.visualization import plot_coupling_map, plot_error_map

from dqcmap import ControllerConfig
from dqcmap.evaluator import Eval
from dqcmap.utils import check_swap_needed, get_cif_qubit_pairs, get_synthetic_dqc
from dqcmap.utils.cm import CmHelper

# # logger = logging.getLogger("dqcmap.passes.dm_layout")
# logger = logging.getLogger("qiskit.transpiler")
# logger.setLevel("DEBUG")
# logger.disabled = False

# Set up logging
logger = logging.getLogger()
logger.setLevel(
    logging.DEBUG
)  # Set the logger to the desired level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

# Create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# Create formatter
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Add formatter to ch
ch.setFormatter(formatter)

# Add ch to logger
logger.addHandler(ch)


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=str, default=10, help="Number of qubits")
    parser.add_argument(
        "--p",
        default=0.5,
        type=float,
        help="Probability of generating conditional gates",
    )
    parser.add_argument("--seed", type=int, default=1900, help="Random seed")
    parser.add_argument(
        "--c", type=int, default=1, help="Number of circuits for certain num_qubits"
    )
    parser.add_argument(
        "--init-layout-type",
        type=str,
        default="null",
        help="Methodology to set the initial layout",
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


def get_init_layout(init_layout_type: str, qc: QuantumCircuit, cm: List[List[int]]):
    """Generate intial layout based on specified type
    Args:
        init_layout_type: Methodology to generate initial layout
        qc: Quantum circuit.
        cm: coupling_map in list format
    """
    if init_layout_type == "null":
        return None
    if init_layout_type == "trivial":
        return CmHelper.gen_trivial_connected_region(qc, cm)

    raise NotImplementedError(f"Unsupported initial layout type: {init_layout_type}")


def gen_qc(num_qc, num_qubits, depth, cond_ratio, use_qiskit, seed_base=1900):
    qc_lst = []

    for idx in range(num_qc):
        # https://github.com/Zhaoyilunnn/dqc-map/issues/3
        # due to the above issue, currently we do not rely on qasm files
        # instead, we generate circuits dynamically
        # reproducibility is guaranteed by setting fixed random seed
        # qc = get_benchmark(num_qubits, depth, args.p, False, idx)
        qc = get_synthetic_dqc(
            num_qubits,
            depth,
            cond_ratio=cond_ratio,
            use_qiskit=use_qiskit,
            seed=seed_base + idx,
        )
        qc_lst.append(qc)
    return qc_lst


def parse_num_qubits(args_qubits: str | int):
    if isinstance(args_qubits, int):
        return [args_qubits]
    if isinstance(args_qubits, str):
        try:
            qubit_lst = [int(q) for q in args_qubits.split(",")]
            return qubit_lst
        except Exception as e:
            raise ValueError(
                f"--n option should be a digit or a list of digits splitted by a comma, i.e., 1,2,3,4"
            )


def main():
    args = get_args()
    nq_lst = parse_num_qubits(args.n)  # list of `num_qubits`
    num_circuits = args.c
    seed = args.seed
    name = args.init_layout_type
    dev = Fake127QPulseV1()
    # print(dev.configuration().coupling_map)
    cm = dev.configuration().coupling_map

    percent_inter_res_dict = {}
    runtime_res_dict = {}
    num_op_res_dict = {}
    # for layout_method in ["dqcmap", "sabre"]:

    # print result table header
    print("num_qubits\tinit_layout\tpercent_inter\truntime\tnum_op")

    for n in nq_lst:
        qc_lst = gen_qc(num_circuits, n, n, args.p, False, seed_base=seed)
        for qc in qc_lst:
            for layout_method in ["dqcmap"]:
                for name in ["null", "trivial"]:  # name of initial layout methodology
                    percent_inter_res_dict.setdefault(name, [])
                    runtime_res_dict.setdefault(name, [])
                    num_op_res_dict.setdefault(name, [])
                    init_layout = get_init_layout(name, qc, cm)
                    # print(qasm2.dumps(qc))
                    # print(qasm3.dumps(qc))
                    # print(qc.draw("text"))

                    tqc = transpile(
                        qc,
                        backend=dev,
                        initial_layout=init_layout,
                        layout_method=layout_method,
                        seed_transpiler=seed,
                    )
                    # tqc = transpile(qc, backend=dev, seed_transpiler=seed)
                    # print(qasm2.dumps(qc))
                    # print(qasm3.dumps(qc))
                    # print(qc.draw("text"))
                    layout = tqc.layout
                    # print(sorted(layout.initial_virtual_layout(filter_ancillas=True)._p2v.keys()))
                    # print(layout.initial_virtual_layout(filter_ancillas=True))
                    # print(sorted(layout.final_virtual_layout(filter_ancillas=True)._p2v.keys()))
                    # print(layout.final_virtual_layout(filter_ancillas=True))
                    final_layout = layout.final_virtual_layout(filter_ancillas=True)
                    swap_needed = check_swap_needed(qc, final_layout, cm)
                    logger.debug(f"Final mapping needs inserting swap? {swap_needed}")

                    sched = schedule(tqc, backend=dev)
                    # print(f"duration: {sched.duration}")

                    conf = ControllerConfig(127, 10)
                    evaluator = Eval(conf)
                    total_latency = evaluator(tqc, dev)
                    gate_latency = evaluator.gate_latency
                    ctrl_latency = evaluator.ctrl_latency
                    inner = evaluator.inner_latency
                    inter = evaluator.inter_latency

                    percent_inter_res_dict[name].append(inter / total_latency)
                    runtime_res_dict[name].append(total_latency)
                    num_op_res_dict[name].append(len(tqc.data))

        for name, res_lst in percent_inter_res_dict.items():
            percent = np.mean(res_lst)
            runtime = np.mean(runtime_res_dict[name])
            num_op = np.mean(num_op_res_dict[name])
            print(f"{n}\t{name}\t{percent}\t{runtime}\t{num_op}")


if __name__ == "__main__":
    main()
