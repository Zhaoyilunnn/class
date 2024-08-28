import copy
import math

import rustworkx as rx
from qiskit import QuantumCircuit
from qiskit.circuit.random.utils import random_circuit
from qiskit.providers.fake_provider import Fake27QPulseV1, Fake127QPulseV1
from qiskit.providers.models import BackendProperties

from dqcmap.utils import get_cif_qubit_pairs
from dqcmap.utils.cm import CmHelper
from dqcmap.utils.misc import update_backend_cx_time, update_backend_cx_time_v2


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


def test_update_backend_cx_time_v2():
    dev = Fake127QPulseV1()
    defs = copy.deepcopy(dev.defaults().to_dict())  # used for comparison
    update_backend_cx_time_v2(dev, 0.5)
    defs_dict = dev._defaults.to_dict()

    assert "cmd_def" in defs_dict
    cmd_def = defs_dict["cmd_def"]

    for i, cmd in enumerate(cmd_def):
        if "qubits" in cmd and len(cmd["qubits"]) == 2:
            # found two qubit gate pulse definitions
            assert "sequence" in cmd
            sequence = cmd["sequence"]

            for j, seq in enumerate(sequence):
                if "parameters" in seq:
                    param = seq["parameters"]
                    if "duration" in param:
                        dur = param["duration"]

                        dur_orig = defs["cmd_def"][i]["sequence"][j]["parameters"][
                            "duration"
                        ]
                        assert dur == int(dur_orig * 0.5)
                    if "width" in param:
                        wid = param["width"]

                        wid_orig = defs["cmd_def"][i]["sequence"][j]["parameters"][
                            "width"
                        ]
                        assert wid == int(wid_orig * 0.5)


class TestCmHelper:
    def test_gen_random_connected_regions(self):
        dev = Fake27QPulseV1()
        cm = dev.configuration().coupling_map

        # Get subgraph list
        sg_lst, _ = CmHelper.gen_random_connected_regions(cm, 5, save_fig=False)

        for sg in sg_lst:
            assert rx.is_connected(sg)

    def test_to_single_direct(self):
        cm = [[0, 1], [1, 0], [2, 3], [3, 2], [1, 2]]

        # single-direction coupling map
        sd_cm = CmHelper.to_single_direct(cm)

        assert sd_cm == [[0, 1], [2, 3], [1, 2]]
