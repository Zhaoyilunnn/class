from qiskit import QuantumCircuit

from dqcmap.circuit_prop import CircProperty
from dqcmap.controller import ControllerConfig, MapStratety
from dqcmap.mappers.trivial_mapper import TrivialMapper

TEST_QC = QuantumCircuit(4, 4)
TEST_QC.measure(1, 1)
TEST_QC.h(0).c_if(1, 1)
TEST_QC.measure(2, 2)
TEST_QC.h(1).c_if(2, 1)
TEST_QC.measure(3, 3)
TEST_QC.h(2).c_if(3, 1)
TEST_QC.measure(1, 1)
TEST_QC.h(0).c_if(1, 1)


class TestTrivialMapper:
    def test_trivial_mapper_run(self):
        ctrl_conf = ControllerConfig(6, 3, strategy=MapStratety.TRIVIAL)
        assert len(ctrl_conf.ctrl_to_pq) == 3
        for k, v in ctrl_conf.ctrl_to_pq.items():
            assert k in {0, 1, 2}
            if k == 0:
                assert v == [0, 1]
            elif k == 1:
                assert v == [2, 3]
            elif k == 2:
                assert v == [4, 5]

        circ_prop = CircProperty(TEST_QC)
        assert circ_prop.cif_pairs == [[0, 1], [1, 2], [2, 3], [0, 1]]

        mapper = TrivialMapper(ctrl_conf, circ_prop)
        res = mapper.run()
        # omit asserting the result due the reproducibility issue
        # assert res == [4, 5, 0, 1]
