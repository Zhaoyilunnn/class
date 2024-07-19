import math

import rustworkx as rx
from qiskit import QuantumCircuit
from qiskit.circuit.random.utils import random_circuit
from qiskit.providers.fake_provider import Fake27QPulseV1, Fake127QPulseV1
from qiskit.providers.models import BackendProperties

from dqcmap.utils import get_cif_qubit_pairs
from dqcmap.utils.cm import CmHelper
from dqcmap.utils.misc import update_backend_cx_time


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


def test_update_backend_cx_time():
    dev = Fake127QPulseV1()

    update_backend_cx_time(dev, 80)

    for item in dev.properties().to_dict()["gates"]:
        if len(item["qubits"]) == 2:
            for dnuv in item["parameters"]:
                if dnuv["name"] == "gate_length":
                    assert math.isclose(dnuv["value"], 80)


class TestCmHelper:
    def test_gen_random_connected_regions(self):
        dev = Fake27QPulseV1()
        cm = dev.configuration().coupling_map

        # Get subgraph list
        sg_lst, _ = CmHelper.gen_random_connected_regions(cm, 5, save_fig=True)

        for sg in sg_lst:
            assert rx.is_connected(sg)

    def test_to_single_direct(self):
        cm = [[0, 1], [1, 0], [2, 3], [3, 2], [1, 2]]

        # single-direction coupling map
        sd_cm = CmHelper.to_single_direct(cm)

        assert sd_cm == [[0, 1], [2, 3], [1, 2]]
