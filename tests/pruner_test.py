from dqcmap.pruners import TrivialPruner

"""
Consider following coupling map

0--1--2
|  |  |
3--4--5

Subgraphs are

0   1   2
|   |   |
3 , 4,  5

"""

CM = [
    [0, 1],
    [1, 0],
    [1, 2],
    [2, 1],
    [0, 3],
    [3, 0],
    [3, 4],
    [4, 3],
    [1, 4],
    [4, 1],
    [4, 5],
    [5, 4],
    [2, 5],
    [5, 2],
]
SG_NODES_LIST = [[0, 3], [1, 4], [2, 5]]


class TestTrivialPruner:
    pruner = TrivialPruner(SG_NODES_LIST, CM)

    def test_edges_inter_sg(self):
        expected_edges = [
            [0, 1],
            [1, 0],
            [3, 4],
            [4, 3],
            [1, 2],
            [2, 1],
            [4, 5],
            [5, 4],
        ]

        for e in expected_edges:
            assert e in self.pruner._edges

    def test_pq2sg(self):
        """Test if the subgraph to physical qubit mapping is as expected"""
        assert self.pruner._pq2sg is not None
        assert self.pruner._pq2sg[0] == 0
        assert self.pruner._pq2sg[3] == 0
        assert self.pruner._pq2sg[1] == 1
        assert self.pruner._pq2sg[4] == 1
        assert self.pruner._pq2sg[2] == 2
        assert self.pruner._pq2sg[5] == 2

    def test_run(self):
        cm = self.pruner.run()
        assert len(cm) < len(self.pruner._cm)
