from qiskit import QuantumCircuit

from dqcmap.circuit_prop import CircProperty


def test_layout_cif_pairs():
    qc = QuantumCircuit(4, 4)
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.cx(0, 1)
    qc.measure(1, 1)
    qc.x(0).c_if(1, 1)

    circ_prop = CircProperty(qc)

    pairs = circ_prop.layout_cif_pairs([0, 3, 2, 1])

    assert pairs == [[0, 3]]
