"""This script analyzes the fidelity between dqc-map (A) and baseline (B)"""

import argparse
import copy
import random

import numpy as np
import qiskit
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.random.utils import random_circuit
from qiskit.providers.fake_provider import Fake127QPulseV1
from qiskit.result.mitigation.utils import counts_to_vector
from qiskit_aer import Aer
from qiskit_aer.noise import noise_model


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", default=10, type=int, help="Number of qubits")
    parser.add_argument("--d", default=10, type=int, help="Circuit depth")
    parser.add_argument(
        "--s",
        "--swap-overhead",
        dest="so",
        type=int,
        default="5",
        help="Number of CNOTs that A is more than B",
    )
    parser.add_argument(
        "--c",
        "--communication-overhead",
        dest="co",
        type=int,
        default=50,
        help="Number of ICC (inter-controller communication steps) that B has more than A",
    )
    return parser.parse_args()


ARGS = get_args()


def tvd(p_0: np.ndarray, p_1: np.ndarray):
    """Calculate the total variation distance between two probability distributions"""


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


def to_A(qc: QuantumCircuit):
    """A has more cnots than B"""
    qc_A = copy.deepcopy(qc)

    for _ in range(ARGS.so):
        q0 = random.randint(0, ARGS.n - 1)
        q1 = random.randint(0, ARGS.n - 1)
        while q0 == q1:
            q1 = random.randint(0, ARGS.n - 1)
        qc_A.cx(q0, q1)

    qc_A.measure_all()

    return qc_A


def to_B(qc: QuantumCircuit):
    """B has more ICC than A"""
    qc_B = copy.deepcopy(qc)

    # delay_period =
    qc_B.delay(500 * ARGS.co, unit="ns")

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

    prob_A = counts_to_vector(counts_A, ARGS.n)
    prob_B = counts_to_vector(counts_B, ARGS.n)

    return prob_A, prob_B


def run_noisy(qc_A: QuantumCircuit, qc_B: QuantumCircuit):
    dev = Fake127QPulseV1()

    tqc_A = transpile(qc_A, backend=dev)
    tqc_B = transpile(qc_B, backend=dev)

    res_A = dev.run(tqc_A).result()
    res_B = dev.run(tqc_B).result()

    counts_A = res_A.get_counts(tqc_A)
    counts_B = res_B.get_counts(tqc_B)

    prob_A = counts_to_vector(counts_A, ARGS.n)
    prob_B = counts_to_vector(counts_B, ARGS.n)

    return prob_A, prob_B


def main():
    qc = gen_circuit()
    qc_A = to_A(qc)
    qc_B = to_B(qc)

    prob_A, prob_B = run_ideal(qc_A, qc_B)

    noisy_prob_A, noisy_prob_B = run_noisy(qc_A, qc_B)


if __name__ == "__main__":
    main()
