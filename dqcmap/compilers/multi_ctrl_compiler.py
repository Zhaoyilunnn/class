from qiskit import QuantumCircuit, transpile
from qiskit.providers import Backend, BackendV1, BackendV2

from dqcmap.basecompiler import BaseCompiler
from dqcmap.controller import ControllerConfig, MapStratety
from dqcmap.pruners import virtual_prune


class MultiCtrlCompiler(BaseCompiler):
    """
    Compile a qc across regions controlled by different controllers

    It will try to avoid cross-controller feedback
    """

    def __init__(self, ctrl_conf: ControllerConfig):
        assert ctrl_conf.strategy is MapStratety.CONNECT
        self._sg_nodes_lst = self._construct_sg_nodes_lst(ctrl_conf)

    def _construct_sg_nodes_lst(self, ctrl_conf: ControllerConfig):
        """Transform ``ctrl_to_pq`` to list of subgraphs"""
        sg_nodes_lst = []
        for _, sg_nodes in ctrl_conf.ctrl_to_pq.items():
            sg_nodes_lst.append(sg_nodes)
        assert all(isinstance(sg_nodes, list) for sg_nodes in sg_nodes_lst)
        return sg_nodes_lst

    def run(
        self,
        qc: QuantumCircuit,
        backend: Backend,
        initial_layout=None,
        layout_method=None,
        routing_method=None,
        seed_transpiler=None,
        opt_level=1,
    ):
        if isinstance(backend, BackendV1):
            cm = backend.configuration().coupling_map
        elif isinstance(backend, BackendV2):
            cm = backend.coupling_map
        else:
            raise ValueError(f"Unknown backend type: {backend}")

        if opt_level == 1:
            pruned_cm = virtual_prune(cm, self._sg_nodes_lst)
        elif opt_level == 2:
            pruned_cm = virtual_prune(
                cm, self._sg_nodes_lst, pruning_method="trivial_v2", prob=0.5
            )
        else:
            raise NotImplementedError(f"Unsupported optimization level {opt_level}")

        tqc = transpile(
            qc,
            backend=backend,
            coupling_map=pruned_cm,
            layout_method=layout_method,
            routing_method=routing_method,
            seed_transpiler=seed_transpiler,
        )

        return tqc
