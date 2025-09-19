"""This script analyzes the fidelity between dqc-map (A) and baseline (B)"""

import argparse
import copy
import random
from time import sleep

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.random.utils import random_circuit
from qiskit.result.mitigation.utils import counts_to_vector
from qiskit_aer import Aer
from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_ibm_runtime import SamplerV2 as Sampler
from qiskit_ibm_runtime.fake_provider import FakeOsaka

SERVICE = QiskitRuntimeService()

DELTA = 500


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", default=2, type=int, help="Number of qubits")
    parser.add_argument("--d", default=2, type=int, help="Circuit depth")
    parser.add_argument(
        "--s",
        "--swap-overhead",
        dest="so",
        type=int,
        default=1,
        help="Number of CNOTs that A is more than B",
    )
    parser.add_argument(
        "--c",
        "--communication-overhead",
        dest="co",
        type=int,
        default=5,
        help="Number of ICC (inter-controller communication steps) that B has more than A",
    )
    parser.add_argument(
        "--scan",
        dest="scan",
        default=1,
        help="Whether to run a series of experiments with the number of swap overhead increase",
    )
    return parser.parse_args()


ARGS = get_args()


def fidelity(p_0: np.ndarray, p_1: np.ndarray):
    """
    Calculate the total variation distance (TVD) between two probability distributions
    and fidelity = 1 - TVD
    """
    if not np.isclose(np.sum(p_0), 1.0) or not np.isclose(np.sum(p_1), 1.0):
        raise ValueError("The input should be valid probability distributions (sum=1)")

    if len(p_0) != len(p_1):
        raise ValueError("The two distributions should have equal length")

    tvd = 0.5 * np.sum(np.abs(p_0 - p_1))
    return 1 - tvd


def gen_circuit():
    qc_base = QuantumCircuit(ARGS.n)
    for i in range(ARGS.n):
        qc_base.h(i)

    random_layers = random_circuit(
        ARGS.n,
        ARGS.d,
        max_operands=2,
        conditional=False,
        reset=False,
        seed=1900,
        measure=False,
    )

    qc_base.compose(random_layers, qubits=range(ARGS.n), inplace=True)

    return qc_base


def to_A(qc: QuantumCircuit, num_cnots: int = 1):
    """A has more cnots than B"""
    qc_A = copy.deepcopy(qc)

    for _ in range(num_cnots):
        q0 = random.randint(0, ARGS.n - 1)
        q1 = random.randint(0, ARGS.n - 1)
        while q0 == q1:
            q1 = random.randint(0, ARGS.n - 1)
        qc_A.cx(q0, q1)

    qc_A.measure_all()

    return qc_A


def to_B(qc: QuantumCircuit, num_icc: int = 5):
    """B has more ICC than A"""
    qc_B = copy.deepcopy(qc)

    # delay_period =
    qc_B.barrier()
    qc_B.delay(DELTA * num_icc, unit="ns")

    qc_B.measure_all()

    return qc_B


def run_ideal(qc_A: QuantumCircuit, qc_B: QuantumCircuit):
    sim = Aer.get_backend("aer_simulator")

    tqc_A = transpile(qc_A, backend=sim)
    tqc_B = transpile(qc_B, backend=sim)

    res_A = sim.run(tqc_A).result()
    res_B = sim.run(tqc_B).result()

    counts_A = res_A.get_counts(tqc_A)
    counts_B = res_B.get_counts(tqc_B)

    prob_A = counts_to_vector(counts_A, ARGS.n)[0]
    prob_B = counts_to_vector(counts_B, ARGS.n)[0]

    return prob_A, prob_B


def run_noisy_local(qc_A: QuantumCircuit, qc_B: QuantumCircuit):
    """Use noisy simulator"""
    # dev = Fake127QPulseV1()
    dev = FakeOsaka()

    tqc_A = transpile(qc_A, backend=dev)
    tqc_B = transpile(qc_B, backend=dev)

    res_A = dev.run(tqc_A).result()
    res_B = dev.run(tqc_B).result()

    counts_A = res_A.get_counts(tqc_A)
    counts_B = res_B.get_counts(tqc_B)

    prob_A = counts_to_vector(counts_A, ARGS.n)[0]
    prob_B = counts_to_vector(counts_B, ARGS.n)[0]

    return prob_A, prob_B


def run_noisy(qc_A: QuantumCircuit, qc_B: QuantumCircuit):
    """Submit to IBM cloud"""
    # dev = Fake127QPulseV1()
    dev = SERVICE.least_busy(operational=True, simulator=False)

    tqc_A = transpile(qc_A, backend=dev)
    tqc_B = transpile(qc_B, backend=dev)
    print(
        f"post-compilation depth\tdqc-map\t{tqc_A.depth()}\tbaseline\t{tqc_B.depth()}"
    )

    sampler = Sampler(mode=dev)
    sampler.options.default_shots = 1024

    job = sampler.run([tqc_A, tqc_B])
    # job = SERVICE.job("cwrsb4cehebg008j12cg") # for retrieving results
    print(f"job ID is {job.job_id()}")

    while job.status() != "DONE":
        sleep(0.5)

    res_A = job.result()[0]
    res_B = job.result()[1]

    counts_A = res_A.data.meas.get_counts()
    counts_B = res_B.data.meas.get_counts()

    prob_A = counts_to_vector(counts_A, ARGS.n)[0]
    prob_B = counts_to_vector(counts_B, ARGS.n)[0]

    return prob_A, prob_B


def main():
    qc = gen_circuit()

    if ARGS.scan:
        for so in range(1, 11):
            print(f"CNOT overhead={so}\tICC reduction={5 * so}")
            qc_A = to_A(qc, so)
            qc_B = to_B(qc, 5 * so)

            prob_A, prob_B = run_ideal(qc_A, qc_B)

            # noisy_prob_A, noisy_prob_B = run_noisy_local(qc_A, qc_B)  # for test
            noisy_prob_A, noisy_prob_B = run_noisy(qc_A, qc_B)

            fid_A = fidelity(prob_A, noisy_prob_A)
            fid_B = fidelity(prob_B, noisy_prob_B)

            print(f"dqc-map\t{fid_A}\tbaseline\t{fid_B}")

    else:
        qc_A = to_A(qc, num_cnots=ARGS.so)
        qc_B = to_B(qc, num_icc=ARGS.co)

        prob_A, prob_B = run_ideal(qc_A, qc_B)

        # noisy_prob_A, noisy_prob_B = run_noisy_local(qc_A, qc_B)  # for test
        noisy_prob_A, noisy_prob_B = run_noisy(qc_A, qc_B)

        fid_A = fidelity(prob_A, noisy_prob_A)
        fid_B = fidelity(prob_B, noisy_prob_B)

        print(f"dqc-map\t{fid_A}\tbaseline\t{fid_B}")


if __name__ == "__main__":
    main()
