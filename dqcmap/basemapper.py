from abc import ABC, abstractmethod
from typing import List

from dqcmap.circuit_prop import CircProperty
from dqcmap.controller import ControllerConfig


class BaseMapper(ABC):
    """Find a initial layout considering the controller arch constraints"""

    def __init__(
        self,
        ctrl_conf: ControllerConfig,
        circ_prop: CircProperty,
    ):
        """
        Args:
            ctrl_conf: Mapping between controller id and the physical qubits it connects to.
            cif_pairs: List of qubit pairs, where the first qubit is conditioned on the second.
        """
        self._ctrl_conf = ctrl_conf
        self._circ_prop = circ_prop

    @abstractmethod
    def run(self) -> List[int]:
        """
        Run the mapping process to generate an initial layout in the form of a list,
        where the list index corresponds to the logical qubit id, and the list element
        corresponds to the physical qubit id.
        """
