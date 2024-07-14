from math import isclose

from qiskit import QuantumCircuit, transpile
from qiskit.providers.fake_provider import Fake127QPulseV1

from dqcmap.controller import ControllerConfig
from dqcmap.evaluator import Eval
from dqcmap.utils import get_cif_qubit_pairs


class TestEval:
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.measure(0, 0)
    qc.cx(0, 1).c_if(0, 1)
    cif_pairs = get_cif_qubit_pairs(qc)

    dev = Fake127QPulseV1()
    tqc = transpile(qc, dev)

    conf = ControllerConfig(127, 10)

    def test_get_phy_cond_pairs_true(self):
        e = Eval(TestEval.conf, TestEval.cif_pairs)
        pairs = e.get_phy_cond_pairs(TestEval.tqc, TestEval.dev)

        assert pairs == [[0, 0], [1, 0]]

    def test_get_phy_cond_pairs_false(self):
        e = Eval(TestEval.conf)
        pairs = e.get_phy_cond_pairs(TestEval.tqc, TestEval.dev)

        assert pairs is None

    def test_calc_latency(self):
        e = Eval(TestEval.conf, TestEval.cif_pairs)
        print(TestEval.conf.pq_to_ctrl)
        pairs = [[1, 0], [3, 15]]

        t = e.calc_ctrl_latency(pairs)

        assert isclose(t, 5.5e-7)
