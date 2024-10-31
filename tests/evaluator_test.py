import os
from math import isclose

from qiskit import QuantumCircuit, transpile
from qiskit.providers.fake_provider import Fake127QPulseV1

from dqcmap.controller import ControllerConfig
from dqcmap.evaluator import Eval, EvalV3
from dqcmap.utils import get_cif_qubit_pairs


class TestEval:
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.measure(0, 0)
    qc.cx(0, 1).c_if(0, 1)
    cif_pairs = get_cif_qubit_pairs(qc)

    dev = Fake127QPulseV1()
    tqc = transpile(qc, dev)

    # Here we use the default trivial mapping because the results are reproducible
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

    def test_get_init_layout_ctrl_latency(self):
        e = Eval(TestEval.conf, TestEval.cif_pairs)

        init_layout = [0, 21]

        t = e.get_init_layout_ctrl_latency(TestEval.qc, init_layout)

        assert isclose(t, 5.5e-7)

    def test_eval_v3_ctrl_latency(self):
        e = EvalV3(TestEval.conf)
        qft_path = "benchmarks/veriq-benchmark/dynamic/qft/dqc_qft_4.qasm"
        assert os.path.exists(qft_path)

        qc = QuantumCircuit.from_qasm_file(qft_path)
        pairs = get_cif_qubit_pairs(qc, with_states=True)

        latency = e.calc_ctrl_latency(pairs)

        assert isclose(latency, 5e-8 * 3)
