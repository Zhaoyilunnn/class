use pyo3::prelude::*;
use pyo3::types::PyList;

#[pyclass]
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
