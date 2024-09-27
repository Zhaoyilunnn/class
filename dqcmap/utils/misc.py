import logging
import random
from collections.abc import Iterable
from typing import Any, Dict, List, Optional, Set

from qiskit import ClassicalRegister, QuantumCircuit
from qiskit.circuit import CircuitInstruction, Clbit, Qubit
from qiskit.circuit.random.utils import random_circuit
from qiskit.providers import Backend, BackendV1, BackendV2
from qiskit.providers.fake_provider import FakeQasmBackend
from qiskit.providers.models import PulseDefaults
from qiskit.providers.models.backendproperties import BackendProperties
from qiskit.transpiler import Layout
from qiskit_ibm_runtime.ibm_backend import IBMBackend

logger = logging.getLogger(__name__)


def get_multi_op_list(qc: QuantumCircuit):
    """
    Find and return all operations in a quantum circuit that applies on multiple qubits

    Returns:
        A list of multi-qubit operations. Each op is represented as a list of qubit indices it applies to.
    """

    logger.debug(f"Looking for multi-qubit operations in the quantum circuit")

    res = []
    for val in qc.data:
        op = []
        if isinstance(val, CircuitInstruction):
            operation, qargs = val.operation, val.qubits
            if len(qargs) >= 2 and not (
                hasattr(operation, "condition") and operation.condition is not None
            ):
                for q in qargs:
                    op.append(q._index)
                res.append(op)
    return res


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

    # Map of c register and qubits
    # This is useful because some qasm implementations (especially qasm2)
    # relies on c register results as conditions
    # So that the `condition` will be `ClassicalRegister` instead of `Clbit`
    map_creg_qubits = {}

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
                    if isinstance(c, Clbit):
                        map_creg_qubits.setdefault(c._register, [])
                        map_creg_qubits[c._register].append(qargs[i])
            if hasattr(operation, "condition") and operation.condition is not None:
                cond = operation.condition

                logger.debug(f" ===> Condition: {cond}")
                assert len(cond) == 2
                if isinstance(cond[0], Clbit):
                    c = cond[0]
                    for q in qargs:
                        pair = [q, measure_map[c]]
                        pairs.append(pair)
                elif isinstance(cond[0], ClassicalRegister):
                    c = cond[0]
                    cond_q_lst = map_creg_qubits[c]
                    for cond_q in cond_q_lst:
                        for q in qargs:
                            pair = [q, cond_q]
                            pairs.append(pair)
                else:
                    assert (
                        False
                    ), "Found an operation with condition neither Clbit nor ClassicalRegister."

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


def _gen_dqc_basic(
    num_qubits: int,
    num_layers: Optional[int] = None,
    gate_set: Optional[Set[Any]] = None,
    cond_ratio: float = 0.5,
    seed: int = 1900,
):
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
                qc.h(apply_qubits[l][n]).c_if(cond_cbit, 1)
            else:
                if control_qubits[l][n] != target_qubits[l][n]:
                    logger.debug(
                        f" ===> Adding cx between lq {control_qubits[l]} and {target_qubits[l]}"
                    )
                    qc.cx(control_qubits[l][n], target_qubits[l][n])

    return qc


def _apply_clifford(qc: QuantumCircuit, qubits: List[int], seed: int = 1900):
    """
    Randomly apply N gates from clifford group to given qubits.

    Args:
        qc (QuantumCircuit): the given quantum circuit.
        seed: random seed
    """
    if len(qubits) >= 2:
        flag_cnot = True
    flag_cnot = False

    gate_set = ["CNOT", "H", "S"]
    for d in qubits:
        g = random.choice(gate_set)
        if g == "CNOT" and flag_cnot:
            targ_lst = [q for q in qubits if q != d]
            t = random.choice(targ_lst)
            qc.cx(d, t)
        elif g == "H":
            qc.h(d)
        elif g == "S":
            qc.s(d)


def _apply_i_c0(qc: QuantumCircuit, qubits: List[int]):
    """
    Apply the I_c1 block to given quantum circuit

    Args:
        qc (QuantumCircuit): The quantum circuit.
        qubits: List of qubit indices to operate on. Say we have N qubits, then the first (N-1)
            are considered as data qubits and the last one is considered as measure qubit.
    """
    assert qc.num_qubits >= len(qubits) and qc.num_clbits >= len(qubits)

    measure_qid = qubits[-1]
    data_qid_lst = qubits[:-1]

    qc.measure(measure_qid, measure_qid)
    cond_cbit = qc.clbits[measure_qid]
    qc.x(measure_qid).c_if(cond_cbit, 1)
    for d in data_qid_lst:
        qc.id(d).c_if(cond_cbit, 1)


def _apply_i_c1(qc: QuantumCircuit, qubits: List[int]):
    """
    Apply the I_c1 block to given quantum circuit

    Args:
        qc (QuantumCircuit): The quantum circuit.
        qubits: List of qubit indices to operate on. Say we have N qubits, then the first (N-1)
            are considered as data qubits and the last one is considered as measure qubit.
    """
    assert qc.num_qubits >= len(qubits) and qc.num_clbits >= len(qubits)

    measure_qid = qubits[-1]
    data_qid_lst = qubits[:-1]

    qc.x(measure_qid)

    qc.measure(measure_qid, measure_qid)
    cond_cbit = qc.clbits[measure_qid]
    qc.x(measure_qid).c_if(cond_cbit, 1)
    for d in data_qid_lst:
        qc.id(d).c_if(cond_cbit, 1)


def _apply_z_c0(qc: QuantumCircuit, qubits: List[int]):
    """
    Apply the Z_c0 block to given quantum circuit

    Args:
        qc (QuantumCircuit): The quantum circuit.
        qubits: List of qubit indices to operate on. Say we have N qubits, then the first (N-1)
            are considered as data qubits and the last one is considered as measure qubit.
    """
    assert qc.num_qubits >= len(qubits) and qc.num_clbits >= len(qubits)

    measure_qid = qubits[-1]
    data_qid_lst = qubits[:-1]

    qc.measure(measure_qid, measure_qid)
    cond_cbit = qc.clbits[measure_qid]
    qc.x(measure_qid).c_if(cond_cbit, 1)
    for d in data_qid_lst:
        qc.z(d).c_if(cond_cbit, 1)


def _apply_z_c1(qc: QuantumCircuit, qubits: List[int]):
    """
    Apply the Z_c1 block to given quantum circuit

    Args:
        qc (QuantumCircuit): The quantum circuit.
        qubits: List of qubit indices to operate on. Say we have N qubits, then the first (N-1)
            are considered as data qubits and the last one is considered as measure qubit.
    """
    assert qc.num_qubits >= len(qubits) and qc.num_clbits >= len(qubits)

    measure_qid = qubits[-1]
    data_qid_lst = qubits[:-1]

    qc.x(measure_qid)
    for d in data_qid_lst:
        qc.z(measure_qid)

    qc.measure(measure_qid, measure_qid)
    cond_cbit = qc.clbits[measure_qid]
    qc.x(measure_qid).c_if(cond_cbit, 1)
    for d in data_qid_lst:
        qc.z(d).c_if(cond_cbit, 1)


def _apply_h_cnot(qc: QuantumCircuit, qubits: List[int]):
    """
    Apply the H_CNOT block to given quantum circuit

    Args:
        qc (QuantumCircuit): The quantum circuit.
        qubits: List of qubit indices to operate on. Say we have N qubits, then the first (N-1)
            are considered as data qubits and the last one is considered as measure qubit.
    """
    assert qc.num_qubits >= len(qubits) and qc.num_clbits >= len(qubits)

    measure_qid = qubits[-1]
    data_qid_lst = qubits[:-1]

    qc.h(measure_qid)
    for d in data_qid_lst:
        qc.cx(measure_qid, d)

    qc.measure(measure_qid, measure_qid)
    cond_cbit = qc.clbits[measure_qid]
    qc.x(measure_qid).c_if(cond_cbit, 1)
    for d in data_qid_lst:
        qc.x(d).c_if(cond_cbit, 1)


def _gen_dqc_rb(
    num_qubits: int,
    num_layers: Optional[int] = None,
    gate_set: Optional[Set[Any]] = None,
    cond_ratio: float = 0.5,
    seed: int = 1900,
):
    """
    Generate dynamic quantum circuit based on randomized benchmarking

    Reference:
        http://arxiv.org/abs/2408.07677, Fig. 1(b)
    """
    block_name_lst = ["H_CNOT", "Z_c1", "Z_c0", "I_c1", "I_c0"]
    random.seed(seed)

    def randomly_split_list(lst):
        random.shuffle(lst)
        result = []
        index = 0

        while index < len(lst):
            if len(lst) - (index) == 1:
                result[-1].extend(lst[index:])
                break

            size = random.randint(2, len(lst) - index)
            result.append(lst[index : index + size])
            index += size

        return result

    qc = QuantumCircuit(num_qubits, num_qubits)
    n_layers = num_qubits if num_layers is None else num_layers

    for _ in range(n_layers):
        qubits = list(range(num_qubits))
        random.shuffle(qubits)

        qgroup_lst = randomly_split_list(qubits)

        for grp in qgroup_lst:
            # flag = random.choice([0, 1])
            # FIXME: currently we only apply F blocks
            flag = 0
            if flag:
                logger.debug(f"Applying clifford block to qubits {grp}")
                _apply_clifford(qc, grp[:-1])
            else:
                f_name = random.choice(block_name_lst)
                logger.debug(
                    f"Applying dynamic circuit block: {f_name} to qubits {grp}"
                )
                if f_name == "H_CNOT":
                    _apply_h_cnot(qc, grp)
                elif f_name == "Z_c1":
                    _apply_z_c1(qc, grp)
                elif f_name == "Z_c0":
                    _apply_z_c0(qc, grp)
                elif f_name == "I_c1":
                    _apply_i_c1(qc, grp)
                elif f_name == "I_c0":
                    _apply_i_c0(qc, grp)

    return qc


def get_synthetic_dqc(
    num_qubits: int,
    num_layers: Optional[int] = None,
    gate_set: Optional[Set[Any]] = None,
    cond_ratio: float = 0.5,
    use_qiskit: bool = True,
    seed: int = 1900,
    use_rb: bool = True,
) -> QuantumCircuit:
    """Generate a random dynamic quantum circuit based on specified configurations,
    In each step, we choose either to add a cif pair or add a cnot gate based on ``cond_ratio``

    Args:
        num_qubits (int): number of qubits.
        num_layers (int): number of layers
        cond_ratio (float): probability of generating a conditional layer.
        use_qiskit (bool): whether to use qiskit builtin ``random_circuit`` method.
        seed (int): random seed for reproducibility.
        use_rb (bool): whether to generate circuit based on arXiv:2408.07677
    """

    if use_qiskit:
        return random_circuit(
            num_qubits, depth=num_layers, max_operands=2, conditional=True
        )

    if use_rb:
        return _gen_dqc_rb(
            num_qubits,
            num_layers=num_layers,
            gate_set=gate_set,
            cond_ratio=cond_ratio,
            seed=seed,
        )

    return _gen_dqc_basic(
        num_qubits,
        num_layers=num_layers,
        gate_set=gate_set,
        cond_ratio=cond_ratio,
        seed=seed,
    )


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

    Notes:
        This method will NOT affect the result of schedule,
        because the pulse durations are defined in another
        place.

    References:
        https://github.com/Qiskit/qiskit/blob/1.1.1/qiskit/providers/fake_provider/backends_v1/fake_127q_pulse/defs_washington.json
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


def update_backend_cx_time_v2(backend: Backend, scale_factor: float):
    """Modify the two-qubit gate time of backend device model

    Args:
        backend: The backend device model.
        scale_factor: New duration will be modified as ``duration * scale_factor``
    """

    if isinstance(backend, FakeQasmBackend) or isinstance(backend, IBMBackend):
        assert hasattr(backend, "defaults")
        backend.defaults()  # call this method to set ``_defaults``

        assert isinstance(backend._defaults, PulseDefaults)

        defs_dict = backend._defaults.to_dict()

        assert "cmd_def" in defs_dict
        cmd_def = defs_dict["cmd_def"]

        for cmd in cmd_def:
            # found two qubit gate pulse definitions
            assert "sequence" in cmd
            sequence = cmd["sequence"]

            for seq in sequence:
                if "parameters" in seq:
                    param = seq["parameters"]
                    if "duration" in param:
                        dur = param["duration"]
                        dur *= scale_factor
                        param["duration"] = int(dur)
                    if "width" in param:
                        width = param["width"]
                        width *= scale_factor
                        param["width"] = int(width)
            # if ("qubits" in cmd and len(cmd["qubits"]) == 2):
            #    # found two qubit gate pulse definitions
            #    assert "sequence" in cmd
            #    sequence = cmd["sequence"]

            #    for seq in sequence:
            #        if "parameters" in seq:
            #            param = seq["parameters"]
            #            if "duration" in param:
            #                dur = param["duration"]
            #                dur *= scale_factor
            #                param["duration"] = int(dur)
            #            if "width" in param:
            #                width = param["width"]
            #                width *= scale_factor
            #                param["width"] = int(width)
            # elif (
            #    "name" in cmd and cmd["name"] == "measure"
            #    ):
            #    assert "sequence" in cmd
            #    sequence = cmd["sequence"]

            #    for seq in sequence:
            #        if "parameters" in seq:
            #            param = seq["parameters"]
            #            if "duration" in param:
            #                dur = param["duration"]
            #                dur *= scale_factor
            #                param["duration"] = int(dur)
            #            if "width" in param:
            #                width = param["width"]
            #                width *= scale_factor
            #                param["width"] = int(width)

        # update _defaults
        backend._defaults = PulseDefaults.from_dict(defs_dict)
