import logging
from typing import Any, List

from qiskit import QuantumCircuit, transpile
from qiskit.circuit import Qubit
from qiskit.compiler import schedule
from qiskit.providers import Backend, BackendV1
from qiskit.pulse import Schedule

from .controller import ControllerConfig
from .utils import get_backend_dt


class Eval:
    """Estimate the final pulse duration time after transpilation

    Example:
        The quantum circuit `qc` should be transpiled::

            conf = ControllerConf(127, 10)
            evaluator = Eval(conf, cif_pairs)
            # dev is the backend
            total_latency = evaluator(qc, dev)
    """

    def __init__(self, ctrl_conf: ControllerConfig, cif_pairs: List[List[Qubit]]):
        """
        Args:
            ctrl_conf: Configuration of controllers
            cif_pairs: Pairs of qubits, where the first is conditioned on the second
        """
        self._layout = None
        self._conf = ctrl_conf
        self._cif_pairs = cif_pairs
        self._orig_latency = None
        self._ctrl_latency = None
        self._inner_ctrl_latency = None
        self._inter_ctrl_latency = None

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

    def __call__(self, qc: QuantumCircuit, backend: Backend):
        """Evaluate the runtime of given quantum circuit"""

        self._init_latency()

        # Get physical qubit pairs
        phy_pairs = self.get_phy_cond_pairs(qc, backend)

        # Calculate the original latency
        self._orig_latency = self.calc_orig_latency(qc, backend)

        # Calculate feedback control latency
        self._ctrl_latency = self.calc_ctrl_latency(phy_pairs)

        # Return the sum of original latency and control latency
        return self._orig_latency + self._ctrl_latency

    def get_phy_cond_pairs(self, qc: QuantumCircuit, backend: Backend):
        """Get the physical qubit pairs, where the first is conditioned on the second"""
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
        logging.debug("Checking final layout")
        for pq in range(qc.num_qubits):
            if pq in final_layout:
                lq = final_layout[pq]  # logical qubit
                logging.debug(f" ===> pq: {pq}, lq: {lq}")
                for pair in self._cif_pairs:
                    if lq is pair[0]:
                        # Then get the corresponding physical qubit
                        cpq = final_layout[pair[1]]
                        logging.debug(
                            f" ==> Found a pq {pq} conditioned on lq: {pair[1]}, which maps to the pq: {cpq}"
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

        ctrl_mapping = self._conf.mapping
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

        self._inner_ctrl_latency = inner_latency
        self._inter_ctrl_latency = inter_latency
        return ctrl_latency
