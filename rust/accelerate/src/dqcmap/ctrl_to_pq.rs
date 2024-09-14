use hashbrown::HashMap;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

#[pyclass]
pub struct Ctrl2Pq {
    // mapping between controller id and the list of physical qubit indexes
    // this controller connects to
    map: HashMap<i32, Vec<i32>>,
}

#[pymethods]
impl Ctrl2Pq {
    #[new]
    fn new(obj: &PyDict) -> PyResult<Self> {
        let mut map = HashMap::new();
        for (k, v) in obj.iter() {
            let key: i32 = k.extract()?;
            let value_list: &PyList = v.extract()?;
            let mut vec = Vec::new();

            for item in value_list.iter() {
                let value: i32 = item.extract()?;
                vec.push(value);
            }

            map.insert(key, vec);
        }

        Ok(Ctrl2Pq { map })
    }
}
