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
from dqcmap.compilers import QiskitDefaultCompiler, SingleCtrlCompiler
from dqcmap.controller import MapStratety
from dqcmap.evaluator import Eval
from dqcmap.utils import check_swap_needed, get_cif_qubit_pairs, get_synthetic_dqc
from dqcmap.utils.cm import CmHelper

COMPILERS = {
    "baseline": QiskitDefaultCompiler,
    "single_ctrl": SingleCtrlCompiler,
}


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
    parser.add_argument(
        "--log", type=int, default=0, help="Whether to output log for debugging."
    )
    parser.add_argument(
        "--comp",
        type=str,
        default="baseline,single_ctrl",
        help="Compiler method or a list of compiler methods splitted by `,`",
    )
    parser.add_argument("--ctrl", type=int, default=10, help="Number of controllers.")

    return parser.parse_args()


ARGS = get_args()

if ARGS.log:
    # Set up logging
    logger = logging.getLogger()
    logger.setLevel(
        logging.DEBUG
    )  # Set the logger to the desired level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    # Create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Add formatter to ch
    ch.setFormatter(formatter)

    # Add ch to logger
    logger.addHandler(ch)

    # logger.disabled = True
else:
    logger = logging.getLogger(__name__)


def debug_qc(qc: QuantumCircuit):
    # print(qasm2.dumps(qc))
    logger.debug(f"Quantum Circuit::")
    logger.debug(
        f" ===> OpenQASM3::\n{qasm3.dumps(qc)}\n ===> Circuit::\n{qc.draw('text')}"
    )


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


# FIXME: delete this function
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
    if init_layout_type == "connected":
        _, regions = CmHelper.gen_random_connected_regions(cm, qc.num_qubits)
        for r in regions:
            if len(r) == qc.num_qubits:
                return r

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


def parse_compiler_methods(args_comp: str):
    comp_lst = args_comp.split(",")
    for comp in comp_lst:
        if not comp in COMPILERS:
            raise ValueError(f"Supported compiler methods are {COMPILERS.keys()}")
    return comp_lst


def main():
    nq_lst = parse_num_qubits(ARGS.n)  # list of `num_qubits`
    num_circuits = ARGS.c
    seed = ARGS.seed
    name = ARGS.init_layout_type
    num_ctrls = ARGS.ctrl
    dev = Fake127QPulseV1()
    cm = dev.configuration().coupling_map

    percent_inter_res_dict = {}
    runtime_res_dict = {}
    num_op_res_dict = {}

    # Create controller configuration and evaluator
    conf = ControllerConfig(
        dev.configuration().n_qubits, num_ctrls, strategy=MapStratety.CONNECT, cm=cm
    )
    evaluator = Eval(conf)

    compiler_name_lst = parse_compiler_methods(ARGS.comp)

    # print result table header
    print("num_qubits\tinit_layout\tpercent_inter\truntime\tnum_op")

    for n in nq_lst:
        qc_lst = gen_qc(num_circuits, n, n, ARGS.p, False, seed_base=seed)
        for qc in qc_lst:
            debug_qc(qc)

            for layout_method in ["dqcmap"]:
                for name in compiler_name_lst:  # name of initial layout methodology
                    percent_inter_res_dict.setdefault(name, [])
                    runtime_res_dict.setdefault(name, [])
                    num_op_res_dict.setdefault(name, [])

                    compiler = COMPILERS[name](conf)

                    tqc = compiler.run(qc, backend=dev, seed_transpiler=seed)
                    layout = tqc.layout
                    final_layout = layout.final_virtual_layout(filter_ancillas=True)
                    logger.debug(f"final layout: \n{final_layout}")
                    swap_needed = check_swap_needed(qc, final_layout, cm)

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
