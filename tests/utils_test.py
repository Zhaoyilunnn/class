from qiskit import QuantumCircuit

from dqcmap.utils import get_cif_qubit_pairs
from dqcmap.utils.cm import CmHelper


def test_get_cif_qubit_pairs():
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.measure(0, 0)
    qc.cx(0, 1).c_if(0, 1)
    pairs = get_cif_qubit_pairs(qc)

    assert len(pairs) == 2
    assert pairs[0][0] is qc.qubits[0]
    assert pairs[1][0] is qc.qubits[1]

    print(qc.draw("text"))


class TestCmHelper:
    def test_gen_trivial_connected_region(self):
        from qiskit.providers.fake_provider import Fake27QPulseV1

        dev = Fake27QPulseV1()
        cm = dev.configuration().coupling_map
        CmHelper.gen_trivial_connected_region(cm)
