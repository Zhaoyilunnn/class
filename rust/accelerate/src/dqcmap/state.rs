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
    pub fn score(&self, swap: &Vec<i32>, gate_order: &Vec<usize>) -> Option<i32> {
        let ctrl2pq = self.ctrl2pq.as_ref()?;
        let ctrl0 = ctrl2pq.get_controller_by_qubit(swap[0])?;
        let ctrl1 = ctrl2pq.get_controller_by_qubit(swap[1])?;
        if ctrl0 != ctrl1 {
            // if the swap involves two qubits controlled by different
            // controllers, we count the number of inter-controller feedbacks
            // before and after this swap, then we use the difference as the score
            let cif_pairs = self.cif_pairs.as_ref()?;
            let involved_pairs: Vec<Vec<i32>> = cif_pairs.get_swap_involved_pairs(swap, gate_order);
            let swapped_pairs: Vec<Vec<i32>> = swap_involved_pairs(&involved_pairs, swap);
            let count_inv: i32 = count_ctrl_pairs(&involved_pairs, ctrl2pq, ctrl0, ctrl1);
            let count_swapped: i32 = count_ctrl_pairs(&swapped_pairs, ctrl2pq, ctrl0, ctrl1);
            Some(count_inv - count_swapped)
        } else {
            Some(0)
        }
    }

    pub fn apply_swap(&mut self, swap: &Vec<i32>, gate_order: &Vec<usize>) {
        if let Some(cif_pairs) = self.cif_pairs.as_mut() {
            cif_pairs.apply_swap(swap, gate_order);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use hashbrown::HashMap;

    #[test]
    fn test_dqcmapstate_score() {
        // Set up a Ctrl2Pq instance with mock controller mappings
        let mut ctrl2pq_map: HashMap<i32, Vec<i32>> = HashMap::new();
        let mut reverse_map: HashMap<i32, i32> = HashMap::new();
        let gate_order: Vec<usize> = Vec::new();

        // Controller 1 controls qubits 0 and 1
        ctrl2pq_map.insert(1, vec![0, 1]);
        // Controller 2 controls qubits 2 and 3
        ctrl2pq_map.insert(2, vec![2, 3]);

        // Reverse mapping from qubit index to controller ID
        reverse_map.insert(0, 1);
        reverse_map.insert(1, 1);
        reverse_map.insert(2, 2);
        reverse_map.insert(3, 2);

        let ctrl2pq: Ctrl2Pq = Ctrl2Pq {
            map: ctrl2pq_map,
            reverse_map,
        };

        // Set up a CifPairs instance with some feedback pairs
        let mut pairs_map: HashMap<usize, Vec<Vec<i32>>> = HashMap::new();
        pairs_map.insert(1, vec![vec![0, 2], vec![1, 3]]); // Feedback pairs between qubits
        let cif_pairs: CifPairs = CifPairs { pairs: pairs_map };

        // Create the DqcMapState with the Ctrl2Pq and CifPairs
        let dqcmap_state: DqcMapState = DqcMapState::new(Some(ctrl2pq), Some(cif_pairs));

        // Test case 1: swap between qubits controlled by different controllers
        let swap1: Vec<i32> = vec![0, 2]; // Qubit 0 (Controller 1) and qubit 2 (Controller 2)
        let score1: Option<i32> = dqcmap_state.score(&swap1, &gate_order);
        assert_eq!(score1, Some(0)); // Cross-controller feedback reduced

        // Test case 2: swap between qubits controlled by the same controller
        let swap2: Vec<i32> = vec![0, 1]; // Qubit 0 and qubit 1 both controlled by Controller 1
        let score2: Option<i32> = dqcmap_state.score(&swap2, &gate_order);
        assert_eq!(score2, Some(0)); // No cross-controller feedback is introduced

        // Test case 3: swap with no involved pairs (no feedback)
        let swap3: Vec<i32> = vec![1, 2]; // Qubit 1 (Controller 1) and qubit 2 (Controller 2)
        let score3: Option<i32> = dqcmap_state.score(&swap3, &gate_order);
        assert_eq!(score3, Some(2)); // No change in feedback count
    }
}
