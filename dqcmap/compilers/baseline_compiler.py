from qiskit import QuantumCircuit, transpile
from qiskit.providers import Backend

from dqcmap.basecompiler import BaseCompiler
from dqcmap.controller import ControllerConfig


class QiskitDefaultCompiler(BaseCompiler):
    """Just a wrapper of qiskit default transpiler"""

    def __init__(self, ctrl_conf: ControllerConfig):
        super().__init__(ctrl_conf)

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
