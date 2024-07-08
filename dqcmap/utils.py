import logging
from qiskit import QuantumCircuit
from qiskit.circuit import CircuitInstruction, Clbit, Qubit


def get_cif_qubit_pairs(qc: QuantumCircuit):
    """Return all qubit pairs in all cif operations

    Args:
        qc (QuantumCircuit): A qiskit quantum circuit instance

    Example:
        ::
            c[1] = measure q[1];
            if (c[1]) {
              h q[8];
            }

        for the above code, the qubit pair is [8, 1]

    """
    # A mapping that records a clbit is measured based on which qubit
    measure_map = {}

    # Result
    pairs = []

    logging.debug(f"{__name__}: Looking for cif in the quantum circuit")
    for val in qc.data:
        if isinstance(val, CircuitInstruction):
            operation, qargs, cargs = val.operation, val.qubits, val.clbits
            if operation.name == "measure":
                assert(len(cargs) == len(qargs))
                for i, c in enumerate(cargs):
                    measure_map[c] = qargs[i]
            if hasattr(operation, "condition") and operation.condition is not None:
                cond = operation.condition

                logging.debug(f" ===> Condition: {cond}")
                assert(len(cond) == 2)
                assert(isinstance(cond[0], Clbit))
                c = cond[0]
                for q in qargs:
                    pair = [q, measure_map[c]]
                    pairs.append(pair)

    logging.debug(f" ===> measure_map: {measure_map}")
    logging.debug(f" ===> result pairs: {pairs}")

    return pairs
