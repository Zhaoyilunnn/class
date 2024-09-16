use pyo3::prelude::*;
use pyo3::types::PyList;

#[pyclass(module = "dqcmap._accelerate.dqcmap")]
#[derive(Clone, Debug)]
pub struct CifPairs {
    // A container storing all cif pairs
    // a cif pair is defined by two qubit indexes, of which one qubit's operation is conditioned on
    // another
    pairs: Vec<Vec<i32>>,
}

#[pymethods]
impl CifPairs {
    #[new]
    fn new(obj: Bound<PyList>) -> PyResult<Self> {
        let mut pairs: Vec<Vec<i32>> = Vec::new();

        // Iterate over each element in the Python list (obj)
        for sublist in obj.iter() {
            // Extract each sublist as a PyList
            let py_sublist: &PyList = sublist.extract()?;

            // Convert PyList to Vec<i32>
            let mut vec: Vec<i32> = Vec::new();
            for item in py_sublist.iter() {
                let value: i32 = item.extract()?; // Extract each element as an i32
                vec.push(value);
            }

            pairs.push(vec); // Push the Vec<i32> into the main pairs vector
        }

        Ok(CifPairs { pairs })
    }
}

impl CifPairs {
    /// Given a swap, return all cif_pairs that contain at least one of the qubit in the swap
    pub fn get_swap_involved_pairs(&self, swap: &Vec<i32>) -> Vec<Vec<i32>> {
        if swap.len() != 2 {
            panic!("Swap must contain exactly two elements");
        }

        let mut involved_pairs = Vec::new();
        for pair in &self.pairs {
            if pair.contains(&swap[0]) || pair.contains(&swap[1]) {
                involved_pairs.push(pair.clone());
            }
        }

        involved_pairs
    }

    /// Apply the selected swap to cif_pairs, essentially update corresponding indexes
    pub fn apply_swap(&mut self, swap: &Vec<i32>) {
        if swap.len() != 2 {
            panic!("Swap must contain exactly two elements");
        }

        for pair in &mut self.pairs {
            for q in pair.iter_mut() {
                if *q == swap[0] {
                    *q = swap[1];
                } else if *q == swap[1] {
                    *q = swap[0];
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_get_swap_involved_pairs() {
        let cif_pairs = CifPairs {
            pairs: vec![vec![1, 2], vec![3, 4], vec![5, 6], vec![1, 6]],
        };

        let swap = vec![1, 5];
        let result = cif_pairs.get_swap_involved_pairs(&swap);
        assert_eq!(result, vec![vec![1, 2], vec![5, 6], vec![1, 6]]);

        let swap = vec![3, 6];
        let result = cif_pairs.get_swap_involved_pairs(&swap);
        assert_eq!(result, vec![vec![3, 4], vec![5, 6], vec![1, 6]]);

        let swap = vec![7, 8];
        let result = cif_pairs.get_swap_involved_pairs(&swap);
        assert!(result.is_empty());

        let invalid_swap = vec![1];
        let result = std::panic::catch_unwind(|| cif_pairs.get_swap_involved_pairs(&invalid_swap));
        assert!(result.is_err());
    }
}
