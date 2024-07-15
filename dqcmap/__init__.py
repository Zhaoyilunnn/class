import sys

import dqcmap._accelerate

from .controller import ControllerConfig
from .evaluator import Eval
from .utils import get_backend_dt, get_cif_qubit_pairs

# Globally define compiled submodules. The normal import mechanism will not find compiled submodules
# in _accelerate because it relies on file paths, but PyO3 generates only one shared library file.
# We manually define them on import so people can directly import qiskit._accelerate.* submodules
# and not have to rely on attribute access.  No action needed for top-level extension packages.
sys.modules["dqcmap._accelerate.circuit"] = dqcmap._accelerate.circuit
sys.modules[
    "dqcmap._accelerate.convert_2q_block_matrix"
] = dqcmap._accelerate.convert_2q_block_matrix
sys.modules["dqcmap._accelerate.dense_layout"] = dqcmap._accelerate.dense_layout
sys.modules["dqcmap._accelerate.error_map"] = dqcmap._accelerate.error_map
sys.modules["dqcmap._accelerate.isometry"] = dqcmap._accelerate.isometry
sys.modules["dqcmap._accelerate.uc_gate"] = dqcmap._accelerate.uc_gate
sys.modules[
    "dqcmap._accelerate.euler_one_qubit_decomposer"
] = dqcmap._accelerate.euler_one_qubit_decomposer
sys.modules["dqcmap._accelerate.nlayout"] = dqcmap._accelerate.nlayout
sys.modules[
    "dqcmap._accelerate.optimize_1q_gates"
] = dqcmap._accelerate.optimize_1q_gates
sys.modules["dqcmap._accelerate.pauli_expval"] = dqcmap._accelerate.pauli_expval
sys.modules["dqcmap._accelerate.results"] = dqcmap._accelerate.results
sys.modules["dqcmap._accelerate.sabre"] = dqcmap._accelerate.sabre
sys.modules["dqcmap._accelerate.sampled_exp_val"] = dqcmap._accelerate.sampled_exp_val
sys.modules["dqcmap._accelerate.sparse_pauli_op"] = dqcmap._accelerate.sparse_pauli_op
sys.modules["dqcmap._accelerate.stochastic_swap"] = dqcmap._accelerate.stochastic_swap
sys.modules[
    "dqcmap._accelerate.two_qubit_decompose"
] = dqcmap._accelerate.two_qubit_decompose
sys.modules["dqcmap._accelerate.vf2_layout"] = dqcmap._accelerate.vf2_layout
