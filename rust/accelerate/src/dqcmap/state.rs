use super::{cif_pairs::CifPairs, ctrl_to_pq::Ctrl2Pq};

fn swap_involved_pairs(involved_pairs: &Vec<Vec<i32>>, swap: &Vec<i32>) -> Vec<Vec<i32>> {
    let mut swapped_pairs = Vec::new();

    for pair in involved_pairs {
        let mut new_pair = pair.clone();

        for qubit in &mut new_pair {
            if *qubit == swap[0] {
                *qubit = swap[1];
            } else if *qubit == swap[1] {
                *qubit = swap[0];
            }
        }

        swapped_pairs.push(new_pair);
    }

    swapped_pairs
}

fn count_ctrl_pairs(
    involved_pairs: &Vec<Vec<i32>>,
    ctrl2pq: &Ctrl2Pq,
    ctrl0: &i32,
    ctrl1: &i32,
) -> i32 {
    let mut count = 0;

    for pair in involved_pairs {
        let c0 = ctrl2pq.get_controller_by_qubit(pair[0]);
        let c1 = ctrl2pq.get_controller_by_qubit(pair[1]);

        match (c0, c1) {
            (Some(ctrl_c0), Some(ctrl_c1)) => {
                // we do not need to count the cross-controller feedbacks other than
                // the controllers involved by the swap because they are not changed
                if (ctrl_c0 == ctrl0 && ctrl_c1 == ctrl1) || (ctrl_c0 == ctrl1 && ctrl_c1 == ctrl0)
                {
                    count += 1;
                }
            }
            _ => continue,
        }
    }

    count
}

pub struct DqcMapState {
    pub ctrl2pq: Option<Ctrl2Pq>,
    pub cif_pairs: Option<CifPairs>,
}

impl DqcMapState {
    pub fn new(ctrl2pq: Option<Ctrl2Pq>, cif_pairs: Option<CifPairs>) -> Self {
        DqcMapState { ctrl2pq, cif_pairs }
    }

    /// 0: no additional cross-controller feedback is introduced
    /// -1: one additional cross-controller feedback is introduced
    /// etc
    pub fn score(&self, swap: &Vec<i32>) -> Option<i32> {
        let ctrl2pq = self.ctrl2pq.as_ref()?;
        let ctrl0 = ctrl2pq.get_controller_by_qubit(swap[0])?;
        let ctrl1 = ctrl2pq.get_controller_by_qubit(swap[1])?;
        if ctrl0 != ctrl1 {
            // if the swap involves two qubits controlled by different
            // controllers, we count the number of inter-controller feedbacks
            // before and after this swap, then we use the difference as the score
            let cif_pairs = self.cif_pairs.as_ref()?;
            let involved_pairs: Vec<Vec<i32>> = cif_pairs.get_swap_involved_pairs(swap);
            let swapped_pairs: Vec<Vec<i32>> = swap_involved_pairs(&involved_pairs, swap);
            let count_inv: i32 = count_ctrl_pairs(&involved_pairs, ctrl2pq, ctrl0, ctrl1);
            let count_swapped: i32 = count_ctrl_pairs(&swapped_pairs, ctrl2pq, ctrl0, ctrl1);
            Some(count_inv - count_swapped)
        } else {
            Some(0)
        }
    }

    pub fn apply_swap(&mut self, swap: &Vec<i32>) {
        if let Some(cif_pairs) = self.cif_pairs.as_mut() {
            cif_pairs.apply_swap(swap);
        }
    }
}
