# export RUST_LOG=debug
# for s in 11 22 33 44; do for h in decay dm1; do python exp/bench.py --n 40 --p 0.9 --t 0.2 --c 1 --comp multi_ctrl --parallel 0 --opt 6 --rt dqcswap --rt-trial 1 --heuristic ${h} --seed $s 1>${s}.${h}.stdout 2>${s}.${h}.stderr; done; done

# for h in decay dqcmap; do
#     python exp/bench.py --n 32 --c 1 --t 0.2 --p 0.9 --comp multi_ctrl --parallel 0 --opt 6 --rt dqcswap --heuristic ${h} --bench cc --ctrl 8 --rt-trial 1 --seed $s 2>${s}.${h}.stderr;
# done;

for c in 8 9; do
    for b in cc pe random; do
        python exp/bench.py --n 32 --c 1 --t 0.2 --p 0.9 --comp baseline,multi_ctrl --parallel 0 --opt 6 --rt dqcswap --heuristic decay --bench $b --ctrl $c --rt-trial 1 --wr 1 --wr-path exp/data/route_effect/ctrl_${c};
        python exp/bench.py --n 32 --c 1 --t 0.2 --p 0.9 --comp multi_ctrl --parallel 0 --opt 6 --rt dqcswap --heuristic dqcmap --bench $b --ctrl $c --rt-trial 1 --wr 1 --wr-path exp/data/route_effect/ctrl_${c};
    done
    python exp/plot_res.py --d exp/data/route_effect/ctrl_${c}
done
