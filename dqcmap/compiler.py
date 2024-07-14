import random
from abc import ABC, abstractmethod
from typing import Any, List

from qiskit import QuantumCircuit, transpile
from qiskit.providers import Backend

from dqcmap.controller import ControllerConfig

_COMPILERS = {"connect": None}


class Compiler(ABC):
    @abstractmethod
    def run(
        self,
        qc: QuantumCircuit,
        backend: Backend,
        initial_layout=None,
        layout_method=None,
        routing_method=None,
        seed_transpiler=None,
    ) -> Any:
        """"""


class DqcBaselineCompiler(Compiler):
    """Just a wrapper of qiskit default transpiler"""

    def __init__(self):
        """"""

    def run(
        self,
        qc: QuantumCircuit,
        backend: Backend,
        initial_layout=None,
        layout_method=None,
        routing_method=None,
        seed_transpiler=None,
    ):
        return transpile(
            qc,
            backend=backend,
            initial_layout=initial_layout,
            layout_method=layout_method,
            routing_method=routing_method,
            seed_transpiler=seed_transpiler,
        )


class DqcConnectedCompiler(Compiler):
    """Just an experimental compiler, only work for compiling qc
    with num_qubits <= a controller connected region
    """

    def __init__(
        self,
        ctrl_conf: ControllerConfig,
        num_try_region: int = 2,
        num_trials_per_region: int = 5,
    ):
        """
        Args:
            ctrl_conf: controller configuration.
            num_try_region: Number of qubit regions to try to layout on.
            num_trials_per_region: Number of permutations to try for each region.
        """
        self._conf = ctrl_conf
        self._num_try_region = num_try_region
        self._num_trials_per_region = num_trials_per_region

    def run(
        self,
        qc: QuantumCircuit,
        backend: Backend,
        initial_layout=None,
        layout_method=None,
        routing_method=None,
        seed_transpiler=None,
    ):
        random.seed(seed_transpiler)
        c2pq = self._conf.ctrl_to_pq

        # Get the regions for trying layout on
        regions_to_try = [c2pq[c_idx] for c_idx in range(self._conf.num_controllers)][
            : self._num_try_region
        ]

        tqc_lst = []
        for region in regions_to_try:
            for idx in range(self._num_trials_per_region):
                random.shuffle(region)
                assert len(region) >= qc.num_qubits
                layout = region[: qc.num_qubits]
                tqc = transpile(
                    qc,
                    backend=backend,
                    initial_layout=layout,
                    layout_method=layout_method,
                    routing_method=routing_method,
                    seed_transpiler=seed_transpiler,
                )
                tqc_lst.append(tqc)

        return min(tqc_lst, key=lambda qc: len(qc))


class CompilerFactory:
    @staticmethod
    def get_compiler(name: str):
        """"""
