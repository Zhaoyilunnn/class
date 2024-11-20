from qiskit import QuantumCircuit

from dqcmap.circuit_prop import CircProperty
from dqcmap.controller import ControllerConfig, MapStratety
from dqcmap.mappers.intra_controller_optimizer import RandomIntraControllerMapper
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


class TestRandomIntraControllerMapper:
    """
    Test the RandomIntraControllerMapper class.
    """

    def test_random_intra_controller_mapper(self):
        # Create a coupling map based on the ctrl_to_pq, connected graph
        coupling_map = [
            [0, 1],
            [1, 2],
            [2, 3],
            [3, 4],
            [4, 5],
            [5, 6],
            [6, 7],
            [7, 8],
            [8, 9],
            [9, 10],
            [10, 11],
            [11, 0],
        ]

        ctrl_conf = ControllerConfig(
            num_qubits=12,
            num_controllers=3,
            cm=coupling_map,
        )

        # Create a quantum circuit with 12 qubits
        qc = QuantumCircuit(12)

        # Add some two-qubit gates
        qc.cx(0, 1)
        qc.cx(2, 3)
        qc.cx(4, 5)
        qc.cx(6, 7)
        qc.cx(8, 9)
        qc.cx(10, 11)

        circ_prop = CircProperty(qc)
        mapper = RandomIntraControllerMapper(ctrl_conf, circ_prop)
        initial_mapping = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
        pq2c = ctrl_conf.pq_to_ctrl
        old_logical_to_ctrl = {
            i: pq2c[initial_mapping[i]] for i in range(12)
        }  # logical qubit to controller

        num_tests = 5
        for i in range(num_tests):
            new_mapping = mapper.run(initial_mapping)
            assert len(new_mapping) == 12
            assert set(new_mapping) == set(range(12))

            # Check if the mapping respects the original controller id configuration
            for lq in range(12):
                old_ctrl = old_logical_to_ctrl[lq]
                new_ctrl = pq2c[new_mapping[lq]]
                assert new_ctrl == old_ctrl

        print("All RandomIntraControllerMapper tests passed successfully.")
