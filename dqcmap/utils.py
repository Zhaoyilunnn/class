import logging
import random
from typing import Any, Optional, Set

from qiskit import QuantumCircuit
from qiskit.circuit import CircuitInstruction, Clbit, Qubit
from qiskit.circuit.random.utils import random_circuit
from qiskit.providers import Backend, BackendV1, BackendV2


def get_cif_qubit_pairs(qc: QuantumCircuit):
    """Return all qubit pairs in all cif operations

    Args:
        qc (QuantumCircuit): A qiskit quantum circuit instance

    Example:
        ::
            c[1] = measure q[1];
            if (c[1]) {
              h q[8];
            }

        for the above code, the qubit pair is [8, 1]

    """
    # A mapping that records a clbit is measured based on which qubit
    measure_map = {}

    # Result
    #  here we use list[list[int]], because a qubit may be conditioned on another qubit for many times
    pairs = []

    logging.debug(f"Looking for cif in the quantum circuit")
    for val in qc.data:
        if isinstance(val, CircuitInstruction):
            operation, qargs, cargs = val.operation, val.qubits, val.clbits
            if operation.name == "measure":
                assert len(cargs) == len(qargs)
                for i, c in enumerate(cargs):
                    measure_map[c] = qargs[i]
            if hasattr(operation, "condition") and operation.condition is not None:
                cond = operation.condition

                logging.debug(f" ===> Condition: {cond}")
                assert len(cond) == 2
                assert isinstance(cond[0], Clbit)
                c = cond[0]
                for q in qargs:
                    pair = [q, measure_map[c]]
                    pairs.append(pair)

    logging.debug(f" ===> measure_map: {measure_map}")
    logging.debug(f" ===> result pairs: {pairs}")

    return pairs


def get_backend_dt(backend: Backend) -> float:
    """Get the the dt from backend based on backend types"""

    if isinstance(backend, BackendV1):
        dt = backend.configuration().dt
    elif isinstance(backend, BackendV2):
        dt = backend.dt
    else:
        raise NotImplementedError(f"Unsupported backend {backend}")

    # currently we assume dt is a float value
    assert isinstance(dt, float)
    return dt


def get_synthetic_dqc(
    num_qubits: int,
    num_layers: Optional[int] = None,
    gate_set: Optional[Set[Any]] = None,
    cond_ratio: float = 0.5,
    use_qiskit: bool = True,
) -> QuantumCircuit:
    """Generate a random dynamic quantum circuit based on specified configuration"""

    if use_qiskit:
        return random_circuit(
            num_qubits, depth=num_layers, max_operands=2, conditional=True
        )

    qc = QuantumCircuit(num_qubits, num_qubits)
    n_layers = num_qubits if num_layers is None else num_layers

    measure_qubits = [random.randint(0, num_qubits - 1) for _ in range(n_layers)]
    apply_qubits = [random.randint(0, num_qubits - 1) for _ in range(n_layers)]
    control_qubits = [random.randint(0, num_qubits - 1) for _ in range(n_layers)]
    target_qubits = [random.randint(0, num_qubits - 1) for _ in range(n_layers)]

    for q in range(num_qubits):
        qc.h(q)

    for l in range(n_layers):
        for _ in range(num_qubits):
            seed = random.random()
            if seed < cond_ratio:
                qc.measure(measure_qubits[l], measure_qubits[l])
                qc.h(apply_qubits[l]).c_if(measure_qubits[l], measure_qubits[l])
                if control_qubits[l] != target_qubits[l]:
                    qc.cx(control_qubits[l], target_qubits[l])

    return qc
