import logging
import time
from math import isclose
from typing import Any, List, Optional

from qiskit import QuantumCircuit
from qiskit.circuit import CircuitInstruction, Qubit
from qiskit.compiler import schedule
from qiskit.providers import Backend
from qiskit.pulse import Schedule

from dqcmap.circuit_prop import CircProperty
from dqcmap.utils.misc import get_cif_qubit_pairs

from .controller import ControllerConfig
from .utils import get_backend_dt

logger = logging.getLogger(__name__)


class Eval:
    """Estimate the final pulse duration time after transpilation

    Example:
        The quantum circuit `qc` should be transpiled::

            conf = ControllerConf(127, 10)
            evaluator = Eval(conf, cif_pairs)
            # dev is the backend
            total_latency = evaluator(qc, dev)
    """

    def __init__(
        self, ctrl_conf: ControllerConfig, cif_pairs: Optional[List[List[Qubit]]] = None
    ):
        """
        Args:
            ctrl_conf: Configuration of controllers
            cif_pairs: Pairs of logical qubits, where the first is conditioned on the second
        """
        self._layout = None
        self._conf = ctrl_conf
        self._cif_pairs = cif_pairs
        self._orig_latency = None
        self._ctrl_latency = None
        self._inner_ctrl_latency = None
        self._inter_ctrl_latency = None
        self._num_cif_pairs = None

    @property
    def gate_latency(self):
        if self._orig_latency is None:
            raise ValueError(
                "Please first run the evaluation before getting the value of gate latency"
            )
        return self._orig_latency

    @property
    def ctrl_latency(self):
        if self._ctrl_latency is None:
            raise ValueError(
                "Please first run the evaluation before getting the value of feedback-control latency"
            )
        return self._ctrl_latency

    @property
    def inner_latency(self):
        if self._inner_ctrl_latency is None:
            raise ValueError(
                "Please first run the evaluation before getting the value of inner feedback-control latency"
            )
        return self._inner_ctrl_latency

    @property
    def inter_latency(self):
        if self._inter_ctrl_latency is None:
            raise ValueError(
                "Please first run the evaluation before getting the value of inter feedback-control latency"
            )
        return self._inter_ctrl_latency

    @property
    def num_cif_pairs(self):
        """Return the number of _cross-controller_ cif pairs"""
        if self._num_cif_pairs is None:
            raise ValueError(
                "Please first run the evaluation before getting the value of number of cif pairs"
            )
        return self._num_cif_pairs

    def __call__(self, qc: QuantumCircuit, backend: Backend):
        """Evaluate the runtime of given quantum circuit
        Args:
            qc (QuantumCircuit): The transpiled circuit.
            backend (Backend): The target device model.
        """

        self._init_latency()

        # Get physical qubit pairs
        pairs = get_cif_qubit_pairs(qc)
        # convert to integer value
        pairs = [[q0._index, q1._index] for [q0, q1] in pairs]
        # print(f"Cif pairs after transpilation: {pairs}")

        # Calculate the original latency
        calc_start = time.perf_counter()
        self._orig_latency = self.calc_orig_latency(qc, backend)
        calc_stop = time.perf_counter()
        logger.debug(
            f"Finished calculating gate latency in {calc_stop - calc_start} sec."
        )

        # Calculate feedback control latency
        calc_start = time.perf_counter()
        self._ctrl_latency = self.calc_ctrl_latency(pairs)
        calc_stop = time.perf_counter()
        logger.debug(
            f"Finished calculating control feedback latency in {calc_stop - calc_start} sec."
        )

        # Return the sum of original latency and control latency
        return self._orig_latency + self._ctrl_latency

    def get_init_layout_ctrl_latency(
        self, qc: QuantumCircuit, initial_layout: List[int]
    ):
        """
        Evaluate the ctrl latency given the initial mapping on a *non-transpiled* circuit
        """
        circ_prop = CircProperty(qc)
        cif_pairs = circ_prop.layout_cif_pairs(initial_layout)
        return self.calc_ctrl_latency(cif_pairs)

    # FIXME: delete this function, we should directly get condition pairs from physical qubits
    def get_phy_cond_pairs(self, qc: QuantumCircuit, backend: Backend):
        """Get the physical qubit pairs, where the first is conditioned on the second"""
        if self._cif_pairs is None:
            return None
        if qc.layout is None:
            raise ValueError(
                "The quantum circuit should be transpiled and the layout property should not be None"
            )

        pairs = []

        # Get the final layout
        layout = qc.layout
        assert hasattr(layout, "initial_virtual_layout")
        assert hasattr(layout, "final_virtual_layout")
        final_layout = layout.final_virtual_layout(filter_ancillas=True)

        # For each physical qubit id (pq)
        # 1. Find all its conditional physical qubit and check if they are controlled by the same controller
        # 2. Accumulate duration based on 1
        logger.debug(f"Checking final layout:\n{final_layout}")
        for pq in range(qc.num_qubits):
            if pq in final_layout:
                lq = final_layout[pq]  # logical qubit
                logger.debug(f" ===> pq: {pq}, lq: {lq}")
                for pair in self._cif_pairs:
                    if lq is pair[0]:
                        # Then get the corresponding physical qubit
                        cpq = final_layout[pair[1]]
                        logger.debug(
                            f" ===> Found a pq {pq} conditioned on lq: {pair[1]}, which maps to the pq: {cpq}"
                        )
                        pairs.append([pq, cpq])

        return pairs

    def calc_orig_latency(self, qc: QuantumCircuit, backend: Backend):
        """Calculate the original latency, which only considers gate time"""
        sched = schedule(qc, backend=backend)
        assert isinstance(sched, Schedule)

        dt = get_backend_dt(backend)
        return sched.duration * dt

    def _init_latency(self):
        self._ctrl_latency = 0
        self._orig_latency = 0
        self._inner_ctrl_latency = 0
        self._inter_ctrl_latency = 0

    def calc_ctrl_latency(self, pairs: List[List[int]]):
        """Calculate the feedback control latency
        1. If two qubits are controlled by the same controller, the latency is small
        2. If they're controlled by different controllers, the latency is much larger
        """

        ctrl_latency = 0
        inner_latency = 0
        inter_latency = 0
        num_inter_cif = 0

        ctrl_mapping = self._conf.pq_to_ctrl
        dt_inner = self._conf.dt_inner
        dt_inter = self._conf.dt_inter

        for pair in pairs:
            targ_pq = pair[0]
            ctrl_pq = pair[1]
            assert targ_pq in ctrl_mapping and ctrl_pq in ctrl_mapping
            if ctrl_mapping[targ_pq] == ctrl_mapping[ctrl_pq]:
                # the qubits are controlled by the same controller
                ctrl_latency += dt_inner
                inner_latency += dt_inner
            else:
                # the qubits are controlled by different controller
                ctrl_latency += dt_inter
                inter_latency += dt_inter
                num_inter_cif += 1

        self._inner_ctrl_latency = inner_latency
        self._inter_ctrl_latency = inter_latency
        self._num_cif_pairs = num_inter_cif
        return ctrl_latency


class EvalV2(Eval):
    def calc_orig_latency(self, qc: QuantumCircuit, backend: Backend):
        """
        Only count 1-q operation and 2-q operation time
        1-q: 20 ns
        2-q: 40 ns
        """
        res = 0.0
        for val in qc.data:
            if isinstance(val, CircuitInstruction):
                operation, qargs, cargs = val.operation, val.qubits, val.clbits
                if operation.name != "measure":
                    if len(qargs) == 2:
                        res += 4e-8
                    elif len(qargs) == 1:
                        res += 2e-8

        return res


class EvalV3(EvalV2):
    def __call__(self, qc: QuantumCircuit, backend: Backend):
        """Evaluate the runtime of given quantum circuit
        Args:
            qc (QuantumCircuit): The transpiled circuit.
            backend (Backend): The target device model.
        """

        self._init_latency()

        # Get physical qubit pairs
        pairs = get_cif_qubit_pairs(qc, with_states=True)
        # print(f"Cif pairs after transpilation: {pairs}")

        # Calculate the original latency
        calc_start = time.perf_counter()
        self._orig_latency = self.calc_orig_latency(qc, backend)
        calc_stop = time.perf_counter()
        logger.debug(
            f"Finished calculating gate latency in {calc_stop - calc_start} sec."
        )

        # Calculate feedback control latency
        calc_start = time.perf_counter()
        self._ctrl_latency = self.calc_ctrl_latency(pairs)
        calc_stop = time.perf_counter()
        logger.debug(
            f"Finished calculating control feedback latency in {calc_stop - calc_start} sec."
        )

        # Return the sum of original latency and control latency
        return self._orig_latency + self._ctrl_latency

    def calc_ctrl_latency(self, pairs: List[Any]):
        """Calculate the feedback control latency
        1. If two qubits are controlled by the same controller, the latency is small
        2. If they're controlled by different controllers, the latency is much larger

        In this version, if multiple qubits rely on a single measurement result, the
        latency is counted for only once because we assume one controller can broadcast
        the result to all dependents.
        """

        ctrl_latency = 0
        inner_latency = 0
        inter_latency = 0
        num_inter_cif = 0

        # Given a cif pair, say [0, 1],
        #   1. if the state is True, meaning that the measurement result
        #      of qubit 1 is used for the first time, we add key 1 to this
        #      cache. If the key is already in the cache, accumulate the
        #      latency value of this key.
        #   2. if the state is False, meaning that the measurement result
        #      of qubit 1 is already used before, we check if current latency
        #      larger than that in the cache and update the cache.
        latency_cache = {}

        ctrl_mapping = self._conf.pq_to_ctrl
        dt_inner = self._conf.dt_inner
        dt_inter = self._conf.dt_inter

        for pair in pairs:
            targ_pq = pair[0][0]._index
            ctrl_pq = pair[0][1]._index
            state = pair[1]

            is_inner = ctrl_mapping[targ_pq] == ctrl_mapping[ctrl_pq]

            if state:
                # if one qubit is measured multiple times, we need to evict previous results
                if ctrl_pq in latency_cache:
                    cached_latency = latency_cache[ctrl_pq]
                    if isclose(cached_latency, dt_inner):
                        ctrl_latency += dt_inner
                        inner_latency += dt_inner
                    else:
                        ctrl_latency += dt_inter
                        inter_latency += dt_inter
                        num_inter_cif += 1
                if is_inner:
                    latency_cache[ctrl_pq] = dt_inner
                else:
                    latency_cache[ctrl_pq] = dt_inter
            else:
                # the measurement result is not used for the first time
                # so these cif pairs only need one communication, and the latency
                # is decided by the largest one. So we simply update cache here
                assert ctrl_pq in latency_cache
                if is_inner:
                    cur_latency = dt_inner
                else:
                    cur_latency = dt_inter
                latency_cache[ctrl_pq] = max(latency_cache[ctrl_pq], cur_latency)

        for _, latency in latency_cache.items():
            if isclose(latency, dt_inner):
                ctrl_latency += dt_inner
                inner_latency += dt_inner
            else:
                ctrl_latency += dt_inter
                inter_latency += dt_inter
                num_inter_cif += 1

        self._inner_ctrl_latency = inner_latency
        self._inter_ctrl_latency = inter_latency
        self._num_cif_pairs = num_inter_cif
        return ctrl_latency

    # TODO: implement this function
    def get_init_layout_ctrl_latency(
        self, qc: QuantumCircuit, initial_layout: List[int]
    ):
        return 0
