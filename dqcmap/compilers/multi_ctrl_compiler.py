from qiskit import QuantumCircuit, transpile
from qiskit.providers import Backend, BackendV1, BackendV2

from dqcmap.basecompiler import BaseCompiler
from dqcmap.circuit_prop import CircProperty
from dqcmap.controller import ControllerConfig, MapStratety
from dqcmap.mappers import mapping
from dqcmap.pruners import virtual_prune


class MultiCtrlCompiler(BaseCompiler):
    """
    Compile a qc across regions controlled by different controllers

    It will try to avoid cross-controller feedback
    """

    def __init__(self, ctrl_conf: ControllerConfig):
        super().__init__(ctrl_conf)
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

        # Parameters that are maybe modified by dqcmap compiler
        # and input to qiskit transpiler
        coupling_map = None
        initial_layout = None

        if opt_level == 1:
            coupling_map = virtual_prune(cm, self._sg_nodes_lst)
        elif opt_level == 2:
            coupling_map = virtual_prune(
                cm, self._sg_nodes_lst, pruning_method="trivial_v2", prob=0.5
            )
        elif opt_level == 3:
            # 1. mapping
            circ_prop = CircProperty(qc)
            initial_layout = mapping(self._conf, circ_prop, mapper_name="kl_partition")
        elif opt_level == 4:
            # 1. mapping
            circ_prop = CircProperty(qc)
            initial_layout = mapping(self._conf, circ_prop, mapper_name="heuristic")
            # 2. pruning
            coupling_map = virtual_prune(
                cm, self._sg_nodes_lst, pruning_method="trivial_v2", prob=0.5
            )
        else:
            raise NotImplementedError(f"Unsupported optimization level {opt_level}")

        tqc = transpile(
            qc,
            backend=backend,
            initial_layout=initial_layout,
            coupling_map=coupling_map,
            layout_method=layout_method,
            routing_method=routing_method,
            seed_transpiler=seed_transpiler,
        )

        return tqc
