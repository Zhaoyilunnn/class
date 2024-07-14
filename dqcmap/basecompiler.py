import random
from abc import ABC, abstractmethod
from typing import Any, List

from qiskit import QuantumCircuit, transpile
from qiskit.providers import Backend

from dqcmap.controller import ControllerConfig

_COMPILERS = {"connect": None}


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
    ) -> Any:
        """"""


class CompilerFactory:
    @staticmethod
    def get_compiler(name: str):
        """"""
