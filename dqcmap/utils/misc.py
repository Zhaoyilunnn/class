import logging
import random
from collections.abc import Iterable
from typing import Any, Dict, List, Optional, Set

from qiskit import QuantumCircuit
from qiskit.circuit import CircuitInstruction, Clbit, Qubit
from qiskit.circuit.random.utils import random_circuit
from qiskit.providers import Backend, BackendV1, BackendV2
from qiskit.providers.fake_provider import FakeQasmBackend
from qiskit.providers.models.backendproperties import BackendProperties
from qiskit.transpiler import Layout
from qiskit_ibm_runtime.ibm_backend import IBMBackend

logger = logging.getLogger(__name__)


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

    logger.debug(f"Looking for cif in the quantum circuit")
    for val in qc.data:
        if isinstance(val, CircuitInstruction):
            operation, qargs, cargs = val.operation, val.qubits, val.clbits
            if operation.name == "measure":
                assert len(cargs) == len(qargs)
                for i, c in enumerate(cargs):
                    measure_map[c] = qargs[i]
            if hasattr(operation, "condition") and operation.condition is not None:
                cond = operation.condition

                logger.debug(f" ===> Condition: {cond}")
                assert len(cond) == 2
                assert isinstance(cond[0], Clbit)
                c = cond[0]
                for q in qargs:
                    pair = [q, measure_map[c]]
                    pairs.append(pair)

    logger.debug(f" ===> measure_map: {measure_map}")
    logger.debug(f" ===> result pairs: {pairs}")

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
    seed: int = 1900,
) -> QuantumCircuit:
    """Generate a random dynamic quantum circuit based on specified configurations
    Args:
        num_qubits (int): number of qubits.
        num_layers (int): number of layers
        cond_ratio (float): probability of generating a conditional layer.
        use_qiskit (bool): whether to use qiskit builtin ``random_circuit`` method.
    """

    if use_qiskit:
        return random_circuit(
            num_qubits, depth=num_layers, max_operands=2, conditional=True
        )

    random.seed(seed)
    qc = QuantumCircuit(num_qubits, num_qubits)
    n_layers = num_qubits if num_layers is None else num_layers

    def _gen_rand_indexes():
        return [
            [random.randint(0, num_qubits - 1) for _ in range(num_qubits)]
            for _ in range(n_layers)
        ]

    measure_idxes, apply_qubits, control_qubits, target_qubits = [
        _gen_rand_indexes() for _ in range(4)
    ]

    for q in range(num_qubits):
        qc.h(q)

    # currently each layer only contains measure, h, and cx
    for l in range(n_layers):
        for n in range(num_qubits):
            prob = random.random()
            if prob < cond_ratio:
                qc.measure(measure_idxes[l][n], measure_idxes[l][n])
                cond_cbit = qc.clbits[measure_idxes[l][n]]
                qc.h(apply_qubits[l][n]).c_if(cond_cbit, measure_idxes[l][n])
                if control_qubits[l][n] != target_qubits[l][n]:
                    logger.debug(
                        f" ===> Adding cx between lq {control_qubits[l]} and {target_qubits[l]}"
                    )
                    qc.cx(control_qubits[l][n], target_qubits[l][n])

    return qc


def check_swap_needed(qc: QuantumCircuit, layout: Layout, cm: List[List[int]]) -> bool:
    """
    Args:
        qc (QuantumCircuit): logical quantum circuit before transpilation.
        layout (Layout): final layout after transpilation.
        cm: Coupling map.
    """
    # FIXME: here we only check two-qubit gates
    for val in qc.data:
        if isinstance(val, CircuitInstruction):
            operation, qargs, cargs = val.operation, val.qubits, val.clbits
            if len(qargs) == 2:
                pq0, pq1 = layout[qargs[0]], layout[qargs[1]]
                if not [pq0, pq1] in cm:
                    return True
    return False


def update_backend_cx_time(backend: Backend, new_time: float):
    """
    Modify the two-qubit gate time of backend device model

    Args:
        backend: The backend device model.
        new_time: The time of two-qubit gate to be updated.
    """

    if isinstance(backend, FakeQasmBackend) or isinstance(backend, IBMBackend):
        props = backend.properties()
        assert isinstance(props, BackendProperties)
        props_dict: dict = props.to_dict()
        assert isinstance(props_dict["gates"], Iterable)
        for item in props_dict["gates"]:
            if len(item["qubits"]) == 2:
                for dnuv in item["parameters"]:
                    if dnuv["name"] == "gate_length":
                        dnuv["value"] = new_time

        props = BackendProperties.from_dict(props_dict)
        backend._properties = props
        return

    raise NotImplementedError(f"Unsupported backend type: {type(backend)}")
