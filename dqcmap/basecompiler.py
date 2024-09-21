from abc import ABC, abstractmethod
from typing import Any, List, Union

from qiskit import QuantumCircuit
from qiskit.providers import Backend

from dqcmap.controller import ControllerConfig

_CircuitsT = Union[QuantumCircuit, List[QuantumCircuit]]


class BaseCompiler(ABC):
    def __init__(self, ctrl_conf: ControllerConfig) -> None:
        self._conf = ctrl_conf

    @abstractmethod
    def run(
        self,
        qc: QuantumCircuit,
        backend: Backend,
        initial_layout=None,
        layout_method=None,
        routing_method=None,
        seed_transpiler=None,
        opt_level: int = 1,
        heuristic: str = "dqcmap",
        swap_trials: int = 5,
    ) -> _CircuitsT:
        """
        Run transpilation

        Args:
            qc (QuantumCircuit): The quantum circuit to compile.
            backend (Backend): The targeting backend device model to.
            initial_layout: The initial mapping between logical qubits and physical qubits. (in list format)
                where the list index denotes logical qubit id and the list element is the corresponding
                physical qubit id.
            layout_method: ``layout_method`` in qiskit transpiler.
            routing_method: ``routing_method`` in qiskit transpiler.
            seed_transpiler: ``seed_transpiler`` in qiskit transpiler.
            opt_level: Optimization level in dqcmap compiler, some dqcmap compiler may use this parameter
                to determine the behavior of compilation process. Note that this is different from qiskit transpiler
                optimization level, which is not tunable in dqcmap compilers and
                is always set to be 1 (the default optimization level)
        """
