import random

from qiskit import QuantumCircuit, transpile
from qiskit.providers import Backend

from dqcmap.basecompiler import BaseCompiler
from dqcmap.controller import ControllerConfig


# TODO: impl
class MultiCtrlCompiler(BaseCompiler):
    """
    Compile a qc across regions controlled by different controllers

    It will try to avoid cross-controller feedback
    """

    def __init__(self, ctrl_conf: ControllerConfig):
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
        pass
