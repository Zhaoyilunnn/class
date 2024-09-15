use cif_pairs::CifPairs;
use ctrl_to_pq::Ctrl2Pq;
use pyo3::prelude::*;
use pyo3::{types::PyModule, Bound, PyResult};

pub mod cif_pairs;
pub mod ctrl_to_pq;

#[pymodule]
pub fn dqcmap(m: &Bound<PyModule>) -> PyResult<()> {
    m.add_class::<CifPairs>()?;
    m.add_class::<Ctrl2Pq>()?;
    Ok(())
}
