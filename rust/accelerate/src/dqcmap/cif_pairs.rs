use hashbrown::HashMap;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

#[pyclass(module = "dqcmap._accelerate.dqcmap")]
#[derive(Clone, Debug)]
pub struct CifPairs {
    // A container storing all cif pairs
    // a cif pair is defined by two qubit indexes, of which one qubit's operation is conditioned on
    // another
    pub pairs: HashMap<usize, Vec<Vec<i32>>>,
}

#[pymethods]
impl CifPairs {
    #[new]
    fn new(obj: Bound<PyDict>) -> PyResult<Self> {
        let mut pairs: HashMap<usize, Vec<Vec<i32>>> = HashMap::new();

        for (py_node_id, part_pairs) in obj.iter() {
            let py_node_id: usize = py_node_id.extract()?;

            let py_part_pairs: &PyList = part_pairs.extract()?;

            let mut part_pairs: Vec<Vec<i32>> = Vec::new();

            for sublist in py_part_pairs.iter() {
                let py_sublist: &PyList = sublist.extract()?;
                let mut vec: Vec<i32> = Vec::new();
                for item in py_sublist {
                    let val: i32 = item.extract()?;
                    vec.push(val);
                }

                part_pairs.push(vec);
            }
            pairs.insert(py_node_id, part_pairs);
        }

        Ok(CifPairs { pairs })
    }
}

impl CifPairs {
    /// Given a swap, return all cif_pairs that contain at least one of the qubit in the swap
    pub fn get_swap_involved_pairs(
        &self,
        swap: &Vec<i32>,
        active_nodes: &Vec<usize>,
    ) -> Vec<Vec<i32>> {
        if swap.len() != 2 {
            panic!("Swap must contain exactly two elements");
        }

        let mut involved_pairs = Vec::new();
        for (py_node_id, node_pairs) in &self.pairs {
            if active_nodes.contains(py_node_id) {
                for pair in node_pairs {
                    if pair.contains(&swap[0]) || pair.contains(&swap[1]) {
                        involved_pairs.push(pair.clone());
                    }
                }
            }
        }

        involved_pairs
    }

    /// Apply the selected swap to cif_pairs, essentially update corresponding indexes
    pub fn apply_swap(&mut self, swap: &Vec<i32>, active_nodes: &Vec<usize>) {
        if swap.len() != 2 {
            panic!("Swap must contain exactly two elements");
        }

        for (py_node_id, node_pairs) in self.pairs.iter_mut() {
            if active_nodes.contains(py_node_id) {
                for pair in node_pairs.iter_mut() {
                    for q in pair {
                        if *q == swap[0] {
                            *q = swap[1];
                        } else if *q == swap[1] {
                            *q = swap[0];
                        }
                    }
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use hashbrown::HashMap;

    #[test]
    fn test_get_swap_involved_pairs() {
        // Create a CifPairs instance with a HashMap
        let mut pairs_map: HashMap<usize, Vec<Vec<i32>>> = HashMap::new();
        pairs_map.insert(1, vec![vec![1, 2], vec![3, 4]]);
        pairs_map.insert(2, vec![vec![5, 6], vec![1, 6]]);

        let cif_pairs: CifPairs = CifPairs { pairs: pairs_map };

        let swap: Vec<i32> = vec![1, 5];
        let active_nodes: Vec<usize> = vec![1, 2];
        let active_nodes_2: Vec<usize> = vec![1];
        let mut result: Vec<Vec<i32>> = cif_pairs.get_swap_involved_pairs(&swap, &active_nodes);
        let mut result_2: Vec<Vec<i32>> = cif_pairs.get_swap_involved_pairs(&swap, &active_nodes_2);
        assert_eq!(
            result.sort(),
            vec![vec![1, 2], vec![5, 6], vec![1, 6]].sort()
        );
        assert_eq!(result_2.sort(), vec![vec![1, 2], vec![1, 6]].sort());

        let swap: Vec<i32> = vec![3, 6];
        let mut result: Vec<Vec<i32>> = cif_pairs.get_swap_involved_pairs(&swap, &active_nodes);
        assert_eq!(
            result.sort(),
            vec![vec![3, 4], vec![5, 6], vec![1, 6]].sort()
        );

        let swap: Vec<i32> = vec![7, 8];
        let result: Vec<Vec<i32>> = cif_pairs.get_swap_involved_pairs(&swap, &active_nodes);
        assert!(result.is_empty());

        let invalid_swap: Vec<i32> = vec![1];
        let result: Result<Vec<Vec<i32>>, Box<dyn std::any::Any + Send>> =
            std::panic::catch_unwind(|| {
                cif_pairs.get_swap_involved_pairs(&invalid_swap, &active_nodes)
            });
        assert!(result.is_err());
    }
}
