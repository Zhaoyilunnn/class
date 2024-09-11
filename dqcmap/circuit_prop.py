from qiskit import QuantumCircuit

from dqcmap.utils.misc import get_cif_qubit_pairs, get_multi_op_list


class CircProperty:
    """Extracted characteristics of given quantum circuit
    """

    def __init__(self, qc: QuantumCircuit):
        self._cif_pairs = None
        self._qc = qc
        self._num_qubits = qc.num_qubits
        self._multi_op_list = None
        self._two_qubit_gates = None
        self._two_qubit_pairs = None

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

    @property
    def two_qubit_gates(self):
        """
        Get two-qubit gates qubits indices in the circuit.
        
        Returns:
            A list of two-qubit gate pairs, where each pair contains two qubit indices.

        Note:
            This method only considers gates with exactly two qubits.
            It does not consider multi-qubit gates with more than two qubits.
            and ignores conditional gates.
        """
        if self._two_qubit_gates is None:
            self._two_qubit_gates = []
            for instruction, qargs, _ in self._qc.data:
                if len(qargs) == 2:
                    self._two_qubit_gates.append([qargs[0]._index, qargs[1]._index])
        return self._two_qubit_gates
