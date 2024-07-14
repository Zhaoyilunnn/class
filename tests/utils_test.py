import rustworkx as rx
from qiskit import QuantumCircuit
from qiskit.circuit.random.utils import random_circuit
from qiskit.providers.fake_provider import Fake27QPulseV1

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
        dev = Fake27QPulseV1()
        cm = dev.configuration().coupling_map

        # TODO
        qc = random_circuit(10, 10)
        CmHelper.gen_trivial_connected_region(qc, cm)

    def test_gen_random_connected_regions(self):
        dev = Fake27QPulseV1()
        cm = dev.configuration().coupling_map

        # Get subgraph list
        sg_lst, _ = CmHelper.gen_random_connected_regions(cm, 5, save_fig=True)

        for sg in sg_lst:
            assert rx.is_connected(sg)
