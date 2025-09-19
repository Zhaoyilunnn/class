import copy
import math
import os

import rustworkx as rx
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.providers.fake_provider import Fake27QPulseV1, Fake127QPulseV1

from dqcmap.utils import get_cif_qubit_pairs
from dqcmap.utils.cm import CmHelper
from dqcmap.utils.misc import (
    get_multi_op_list,
    update_backend_cx_time,
    update_backend_cx_time_v2,
)


def test_get_multi_op_list():
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.measure(0, 0)
    qc.cx(0, 1)
    qc.h(1).c_if(0, 0)
    res = get_multi_op_list(qc)
    assert res == [[0, 1]]


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


def test_get_cif_qubit_pairs_dqc_qft():
    qft_path = "benchmarks/veriq-benchmark/dynamic/qft/dqc_qft_4.qasm"
    assert os.path.exists(qft_path)

    qc = QuantumCircuit.from_qasm_file(qft_path)
    pairs = get_cif_qubit_pairs(qc, with_states=True)

    assert len(pairs) == 6

    # Verify qubits correctness
    assert pairs[0][0][0] is qc.qubits[1]
    assert pairs[1][0][0] is qc.qubits[2]
    assert pairs[2][0][0] is qc.qubits[3]
    assert pairs[0][0][1] is qc.qubits[0]
    assert pairs[1][0][1] is qc.qubits[0]
    assert pairs[2][0][1] is qc.qubits[0]

    assert pairs[3][0][0] is qc.qubits[2]
    assert pairs[4][0][0] is qc.qubits[3]
    assert pairs[3][0][1] is qc.qubits[1]
    assert pairs[4][0][1] is qc.qubits[1]

    assert pairs[5][0][0] is qc.qubits[3]
    assert pairs[5][0][1] is qc.qubits[2]

    # Verify states correctness
    assert pairs[0][1] is True
    assert pairs[1][1] is False
    assert pairs[2][1] is False

    assert pairs[3][1] is True
    assert pairs[4][1] is False

    assert pairs[5][1] is True
    print(qc.draw("text"))


def test_get_cif_qubit_pairs_creg_toy():
    creg = ClassicalRegister(2)
    qreg = QuantumRegister(2)
    qc = QuantumCircuit(qreg, creg)
    qc.h(qreg[0])
    qc.measure(qreg[0], creg[0])
    qc.cx(qreg[0], qreg[1]).c_if(creg, 1)
    pairs = get_cif_qubit_pairs(qc)

    assert len(pairs) == 2
    assert pairs[0][0] is qc.qubits[0]
    assert pairs[1][0] is qc.qubits[1]

    print(qc.draw("text"))


def test_get_cif_qubit_pairs_creg_pe():
    pe_path = "benchmarks/veriq-benchmark/dynamic/pe/dqc_pe_4.qasm"
    assert os.path.exists(pe_path)
    qc = QuantumCircuit.from_qasm_file(pe_path)
    pairs = get_cif_qubit_pairs(qc)

    assert len(pairs) == 6

    assert pairs[0][0] is qc.qubits[1]
    assert pairs[1][0] is qc.qubits[2]
    assert pairs[2][0] is qc.qubits[3]
    assert pairs[0][1] is qc.qubits[0]
    assert pairs[1][1] is qc.qubits[0]
    assert pairs[2][1] is qc.qubits[0]

    assert pairs[3][0] is qc.qubits[2]
    assert pairs[4][0] is qc.qubits[3]
    assert pairs[3][1] is qc.qubits[1]
    assert pairs[4][1] is qc.qubits[1]

    assert pairs[5][0] is qc.qubits[3]
    assert pairs[5][1] is qc.qubits[2]

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
