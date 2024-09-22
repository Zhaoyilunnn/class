import argparse
import csv
import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Type

import numpy as np
from joblib import Parallel, delayed
from qiskit import QuantumCircuit, qasm2, qasm3
from qiskit.providers.fake_provider import Fake127QPulseV1

from dqcmap import ControllerConfig
from dqcmap.basecompiler import BaseCompiler
from dqcmap.compilers import QiskitDefaultCompiler, SingleCtrlCompiler
from dqcmap.compilers.multi_ctrl_compiler import MultiCtrlCompiler
from dqcmap.controller import MapStratety
from dqcmap.evaluator import Eval, EvalV2
from dqcmap.exceptions import DqcMapException
from dqcmap.utils import check_swap_needed, get_synthetic_dqc
from dqcmap.utils.cm import CmHelper
from dqcmap.utils.misc import update_backend_cx_time, update_backend_cx_time_v2

COMPILERS: Dict[str, Type[BaseCompiler]] = {
    "baseline": QiskitDefaultCompiler,
    "single_ctrl": SingleCtrlCompiler,
    "multi_ctrl": MultiCtrlCompiler,
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
        "--debug-only",
        type=str,
        default="",
        help="Specifying which module to output debut info.",
    )
    parser.add_argument(
        "--comp",
        type=str,
        default="baseline,single_ctrl",
        help="Compiler method or a list of compiler methods splitted by `,`",
    )
    parser.add_argument("--ctrl", type=int, default=10, help="Number of controllers.")
    parser.add_argument(
        "--parallel",
        type=int,
        default=1,
        help="Whether to run each circuit in parallel. Note that you need to turn off this flag when --log is on.",
    )
    parser.add_argument(
        "--opt",
        type=int,
        default=2,
        help="Optimization level used in dqcmap compiler. Note that this is different from qiskit transipler optimization level",
    )
    parser.add_argument(
        "--t",
        default=0.5,
        type=float,
        help="Specifying the scaling factor of two-qubit gate time. State-of-the-art two-qubit gate time is much smaller than public available devices. So use this config to simulate most recent devices.",
    )
    parser.add_argument(
        "--rt",
        default="dqcswap",
        type=str,
        help="Routing method. For baseline, it will always be set to `sabre`, for multi_ctrl it will be this argument.",
    )
    parser.add_argument(
        "--rt-trial",
        default=5,
        type=int,
        help="Number of parallel swap trials during routing",
    )
    parser.add_argument(
        "--heuristic", default="dqcmap", type=str, help="Heuristic for dqcswap routing."
    )
    parser.add_argument(
        "--wr", default=0, type=int, help="Whether to write results to csv."
    )

    return parser.parse_args()


ARGS = get_args()

if ARGS.log:
    # Set up logging
    if ARGS.debug_only:
        logger = logging.getLogger(ARGS.debug_only)
    else:
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
else:
    logger = logging.getLogger(__name__)


def debug_qc(qc: QuantumCircuit):
    # print(qasm2.dumps(qc))
    logger = logging.getLogger(__name__)
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
            use_rb=False,
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


@dataclass
class Result:
    compiler_method: str = "multi_ctrl"
    runtime: float = 0.0
    perc_inter: float = 0.0
    num_ops: int = 0
    depth: int = 0


def _get_impl_name(compiler_name, opt_level, heuristic, routing_method):
    if compiler_name == "baseline":
        return "baseline"
    if compiler_name == "multi_ctrl":
        if opt_level == 3:
            if routing_method == "dqcswap" and heuristic == "dqcmap":
                return "map+route"
            if routing_method == "dqcswap" and heuristic == "decay":
                return "map"
        if opt_level == 6:
            if routing_method == "dqcswap" and heuristic == "dqcmap":
                return "map+layout+route"
            if routing_method == "dqcswap" and heuristic == "decay":
                return "map+layout"

    return "unknown"


def process_results(result_lst: List[Result | None], num_qubits: int, csv_writer):
    perc_inter_dict = {}
    runtime_dict = {}
    num_op_dict = {}
    depth_dict = {}

    for res in result_lst:
        if not isinstance(res, Result):
            raise DqcMapException(f"Some circuit run failed due to {type(res)}: {res}")

        perc_inter_dict.setdefault(res.compiler_method, [])
        runtime_dict.setdefault(res.compiler_method, [])
        num_op_dict.setdefault(res.compiler_method, [])
        depth_dict.setdefault(res.compiler_method, [])

        perc_inter_dict[res.compiler_method].append(res.perc_inter)
        runtime_dict[res.compiler_method].append(res.runtime)
        num_op_dict[res.compiler_method].append(res.num_ops)
        depth_dict[res.compiler_method].append(res.depth)

    for name, res_lst in perc_inter_dict.items():
        percent = np.mean(res_lst)
        runtime = np.mean(runtime_dict[name])
        num_op = np.mean(num_op_dict[name])
        depth = np.mean(depth_dict[name])
        impl = _get_impl_name(name, ARGS.opt, ARGS.heuristic, ARGS.rt)
        print(f"{num_qubits}\t{name}\t{percent}\t{runtime}\t{num_op}\t{depth}\t{impl}")
        if ARGS.wr and csv_writer is not None:
            csv_writer.writerow(
                [num_qubits, name, percent, runtime, num_op, depth, impl]
            )


def run_circuit(
    qc: QuantumCircuit,
    dev,
    seed,
    cm,
    evaluator,
    conf,
    layout_method,
    compiler_name,
):
    debug_qc(qc)
    compiler = COMPILERS[compiler_name](conf)

    if compiler_name == "baseline":
        routing_method = "sabre"
        layout_method = "sabre"
    else:
        routing_method = ARGS.rt

    tqc = compiler.run(
        qc,
        backend=dev,
        layout_method=layout_method,
        routing_method=routing_method,
        seed_transpiler=seed,
        opt_level=ARGS.opt,
        heuristic=ARGS.heuristic,
        swap_trials=ARGS.rt_trial,
    )
    layout = tqc.layout
    final_layout = layout.final_virtual_layout(filter_ancillas=True)
    logger = logging.getLogger(__name__)
    logger.debug(f"final layout: \n{final_layout}")
    swap_needed = check_swap_needed(qc, final_layout, cm)

    total_latency = evaluator(tqc, dev)
    gate_latency = evaluator.gate_latency
    ctrl_latency = evaluator.ctrl_latency
    inner = evaluator.inner_latency
    inter = evaluator.inter_latency

    perc_inter = inter / total_latency
    num_op = len(tqc.data)
    depth = tqc.depth()
    # return perc_inter, total_latency, num_op
    return Result(
        compiler_method=compiler_name,
        runtime=total_latency,
        perc_inter=perc_inter,
        num_ops=num_op,
        depth=depth,
    )


def main():
    nq_lst = parse_num_qubits(ARGS.n)  # list of `num_qubits`
    num_circuits = ARGS.c
    seed = ARGS.seed
    name = ARGS.init_layout_type
    num_ctrls = ARGS.ctrl
    dev = Fake127QPulseV1()
    update_backend_cx_time_v2(dev, ARGS.t)
    cm = dev.configuration().coupling_map

    # Create controller configuration and evaluator
    conf = ControllerConfig(
        dev.configuration().n_qubits, num_ctrls, strategy=MapStratety.CONNECT, cm=cm
    )
    # evaluator = EvalV2(conf)
    evaluator = Eval(conf)

    compiler_name_lst = parse_compiler_methods(ARGS.comp)

    # print result table header
    res_file_name = f"exp/{ARGS.comp}_{ARGS.rt}_{ARGS.heuristic}_opt_{ARGS.opt}.csv"
    print("num_qubits\tcompiler_type\tpercent_inter\truntime\tnum_op\tdepth\timpl")
    csv_writer = None
    f = None
    if ARGS.wr:
        f = open(res_file_name, "w")
        csv_writer = csv.writer(f)
        csv_writer.writerow(
            [
                "num_qubits",
                "compiler_type",
                "percent_inter",
                "runtime",
                "num_op",
                "depth",
                "impl",
            ]
        )

    for n in nq_lst:
        qc_lst = gen_qc(num_circuits, n, n, ARGS.p, False, seed_base=seed)
        if ARGS.parallel:
            results = Parallel(n_jobs=-1)(
                delayed(run_circuit)(
                    qc,
                    dev,
                    seed,
                    cm,
                    evaluator,
                    conf,
                    layout_method,
                    name,
                )
                for qc in qc_lst
                for layout_method in ["dqcmap"]
                for name in compiler_name_lst
            )
            # print(results)
            results = [res for res in results]
        else:
            results = []
            for qc in qc_lst:
                for layout_method in ["dqcmap"]:
                    for name in compiler_name_lst:
                        res = run_circuit(
                            qc,
                            dev,
                            seed,
                            cm,
                            evaluator,
                            conf,
                            layout_method,
                            name,
                        )
                        results.append(res)
        process_results(results, n, csv_writer)

    if f:
        f.close()


if __name__ == "__main__":
    main()
