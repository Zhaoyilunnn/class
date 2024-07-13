import logging
from typing import List, Optional

import numpy as np
import rustworkx


class ControllerConfig:
    def __init__(
        self,
        num_qubits: int,
        num_controllers: int,
        dt_inner: Optional[float] = None,
        dt_inter: Optional[float] = None,
        strategy: str = "simple",
    ):
        self._dt_inner = dt_inner if dt_inner is not None else 5e-8
        self._dt_inter = dt_inter if dt_inter is not None else 5e-7
        self._strategy = strategy
        if self._dt_inter < 5 * self._dt_inner:
            logging.warning(
                f"Latency within the same controller is expected to be at least 5x shorter than the latency across different controllers"
            )
        assert (
            num_qubits > 0 and num_controllers > 0 and num_qubits > 2 * num_controllers
        )
        self._num_qubits = num_qubits
        self._num_controllers = num_controllers
        self._pq2c = {}  # mapping between physical qubits and controllers

    # TODO: impl of different mapping strategy
    @property
    def mapping(self):
        """The mapping between physical qubit id and controller id"""
        if not self._pq2c:
            self._pq2c = self._gen_mapping()
        return self._pq2c

    def _gen_mapping(self):
        pq2c = {}
        if self._strategy == "simple":
            pq_lst = range(self._num_qubits)
            arr = np.array(pq_lst, dtype=int)
            split_lst = np.array_split(arr, self._num_controllers)
            for idx, sub_lst in enumerate(split_lst):
                logging.debug(
                    f"Controller: {idx}, connects {len(sub_lst)} physical qubits: {sub_lst.tolist()}"
                )
                for pq in sub_lst:
                    pq2c[pq] = idx
        else:
            raise NotImplementedError(f"Unsupported mapping strategy: {self._strategy}")

        return pq2c

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
