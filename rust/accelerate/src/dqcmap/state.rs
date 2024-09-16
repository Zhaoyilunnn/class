use super::{cif_pairs::CifPairs, ctrl_to_pq::Ctrl2Pq};

pub struct DqcMapState<'a> {
    pub ctrl2pq: Option<&'a Ctrl2Pq>,
    pub cif_pairs: Option<&'a CifPairs>,
}

impl<'a> DqcMapState<'a> {
    pub fn new(ctrl2pq: Option<&'a Ctrl2Pq>, cif_pairs: Option<&'a CifPairs>) -> Self {
        DqcMapState { ctrl2pq, cif_pairs }
    }

    pub fn score(&self, swap: &Vec<i32>) -> i32 {
        0
    }
}
