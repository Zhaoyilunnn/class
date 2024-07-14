import logging
from enum import Enum
from typing import List, Optional

import numpy as np
import rustworkx

from dqcmap.utils.cm import CmHelper

logger = logging.getLogger(__name__)


class MapStratety(Enum):
    """Enumeration of controller mapping strategy"""

    TRIVIAL = 1
    CONNECT = 2


class ControllerConfig:
    def __init__(
        self,
        num_qubits: int,
        num_controllers: int,
        dt_inner: Optional[float] = None,
        dt_inter: Optional[float] = None,
        strategy: MapStratety = MapStratety.TRIVIAL,
        cm: Optional[List[List[int]]] = None,
    ):
        """Initialzation of a controller Configuration

        Args:
            num_qubits: Number of qubits (total physical qubits in quantum device).
            num_controllers: Number of controllers.
            dt_inter: Control-feedback latency within the same controller.
            dt_inter: Control-feedback latency across different controllers.
            strategy: Name of strategy for generating mapping between controllers and qubits.
            cm: Coupling map of the quantum device.
        """
        self._dt_inner = dt_inner if dt_inner is not None else 5e-8
        self._dt_inter = dt_inter if dt_inter is not None else 5e-7
        self._strategy = strategy
        if self._dt_inter < 5 * self._dt_inner:
            logger.warning(
                f"Latency within the same controller is expected to be at least 5x shorter than the latency across different controllers"
            )
        assert (
            num_qubits > 0 and num_controllers > 0 and num_qubits > 2 * num_controllers
        )
        self._num_qubits = num_qubits
        self._num_controllers = num_controllers
        self._pq2c = {}  # mapping between physical qubits and controllers
        self._cm = cm

    # TODO: impl of different mapping strategy
    @property
    def mapping(self):
        """The mapping between physical qubit id and controller id"""
        if not self._pq2c:
            self._pq2c = self._gen_mapping()
        return self._pq2c

    def _gen_trivial_mapping(self):
        pq2c = {}
        pq_lst = range(self._num_qubits)
        arr = np.array(pq_lst, dtype=int)
        split_lst = np.array_split(arr, self._num_controllers)
        for idx, sub_lst in enumerate(split_lst):
            logger.debug(
                f"Controller: {idx}, connects {len(sub_lst)} physical qubits: {sub_lst.tolist()}"
            )
            for pq in sub_lst:
                pq2c[pq] = idx
        return pq2c

    def _gen_connected_mapping(self):
        pq2c = {}
        region_size = int(np.ceil(self._num_qubits / self._num_controllers))
        _, sg_nodes_lst = CmHelper.gen_trivial_connected_regions(
            self._cm, region_size=region_size
        )

        # There may be some small subgraphs that're not connected
        # merge them into remain_nodes_lst
        remain_nodes_lst = []
        ctrl_idx = 0
        for sg in sg_nodes_lst:
            if len(sg) == region_size:
                for pq in sg:
                    pq2c[pq] = ctrl_idx
                ctrl_idx += 1
            else:
                remain_nodes_lst.extend(sg)

        if len(remain_nodes_lst) > region_size:
            logger.warning(
                f"Merged an unconnected nodes: {remain_nodes_lst} list larger than region size: {region_size}"
            )

        if remain_nodes_lst:
            for pq in remain_nodes_lst:
                pq2c[pq] = ctrl_idx

        return pq2c

    def _gen_mapping(self):
        if self._strategy == MapStratety.TRIVIAL:
            return self._gen_trivial_mapping()
        if self._strategy == MapStratety.CONNECT:
            return self._gen_connected_mapping()

        raise NotImplementedError(f"Unsupported mapping strategy: {self._strategy}")

    @property
    def dt_inner(self):
        """The feedback control latency within the same controller

        References:
            1. https://www.zhinst.com/japan/en/applications/quantum-technologies/quantum-feedback-measurements
            2. https://ieeexplore.ieee.org/document/8675197/
        """
        return self._dt_inner

    @property
    def dt_inter(self):
        """The feedback control latency between different controllers

        References:
            1. https://www.nature.com/articles/s41586-023-06846-3
            2. https://www.zhinst.com/japan/en/applications/quantum-technologies/quantum-feedback-measurements
        """
        return self._dt_inter
