export RUST_LOG=debug
for s in 11 22 33 44; do for h in decay dm1; do python exp/bench.py --n 40 --p 0.9 --t 0.2 --c 1 --comp multi_ctrl --parallel 0 --opt 6 --rt dqcswap --rt-trial 1 --heuristic ${h} --seed $s 1>${s}.${h}.stdout 2>${s}.${h}.stderr; done; done
