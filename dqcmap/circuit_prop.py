from qiskit import QuantumCircuit

from dqcmap.utils.misc import get_cif_qubit_pairs, get_multi_op_list


class CircProperty:
    """Extracted characteristics of given quantum circuit"""

    def __init__(self, qc: QuantumCircuit):
        self._cif_pairs = None
        self._qc = qc
        self._num_qubits = qc.num_qubits
        self._multi_op_list = None

    @property
    def cif_pairs(self):
        if not self._cif_pairs:
            pairs = get_cif_qubit_pairs(self._qc)
            self._cif_pairs = [[q0._index, q1._index] for [q0, q1] in pairs]
        return self._cif_pairs

    @property
    def num_qubits(self):
        return self._num_qubits

    @property
    def multi_op_list(self):
        if not self._multi_op_list:
            self._multi_op_list = get_multi_op_list(self._qc)
        return self._multi_op_list
