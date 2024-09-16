use hashbrown::HashMap;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

#[pyclass(module = "dqcmap._accelerate.dqcmap")]
#[derive(Clone, Debug)]
pub struct Ctrl2Pq {
    // mapping between controller id and the list of physical qubit indexes
    // this controller connects to
    map: HashMap<i32, Vec<i32>>,
    // mapping between (physical) qubit index and controller id
    reverse_map: HashMap<i32, i32>,
}

#[pymethods]
impl Ctrl2Pq {
    #[new]
    fn new(obj: Bound<PyDict>) -> PyResult<Self> {
        let mut map = HashMap::new();
        let mut reverse_map = HashMap::new();
        for (k, v) in obj.iter() {
            let ctrl_id: i32 = k.extract()?;
            let value_list: &PyList = v.extract()?;
            let mut vec = Vec::new();

            for item in value_list.iter() {
                let qubit_idx: i32 = item.extract()?;
                vec.push(qubit_idx);
                reverse_map.insert(qubit_idx, ctrl_id);
            }

            map.insert(ctrl_id, vec);
        }

        Ok(Ctrl2Pq { map, reverse_map })
    }

    pub fn get_controller_by_qubit(&self, qubit_idx: i32) -> Option<&i32> {
        self.reverse_map.get(&qubit_idx)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use pyo3::types::IntoPyDict;
    use pyo3::Python;

    #[test]
    fn test_ctrl2pq_creation() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            // Create a Python dictionary in Rust
            let data = vec![(1, vec![1, 2, 3]), (2, vec![4, 5, 6])];
            let py_dict = data.into_py_dict_bound(py);

            // Create an instance of Ctrl2Pq
            let ctrl2pq = Ctrl2Pq::new(py_dict).unwrap();

            // Check if the mapping is correct
            assert_eq!(ctrl2pq.map.get(&1), Some(&vec![1, 2, 3]));
            assert_eq!(ctrl2pq.map.get(&2), Some(&vec![4, 5, 6]));
        });
    }
}
