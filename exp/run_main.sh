# python exp/bench.py --n 20,30,40,50 --c 1 --comp baseline,multi_ctrl --parallel 0 --opt 6 --rt dqcswap --heuristic decay --wr 1 --bench pe --wr-path exp/data/ctrl_10
# python exp/bench.py --n 20,30,40,50 --c 1 --t 0.2 --p 0.9 --comp baseline,multi_ctrl --parallel 0 --opt 6 --rt dqcswap --heuristic decay --wr 1 --bench random --wr-path exp/data/ctrl_10
#
# python exp/bench.py --n 20,30,40,50 --c 1 --comp baseline,multi_ctrl --parallel 0 --opt 6 --rt dqcswap --heuristic decay --wr 1 --bench pe --ctrl 5 --wr-path exp/data/ctrl_5
# python exp/bench.py --n 20,30,40,50 --c 1 --t 0.2 --p 0.9 --comp baseline,multi_ctrl --parallel 0 --opt 6 --rt dqcswap --heuristic decay --wr 1 --bench random --ctrl 5 --wr-path exp/data/ctrl_5
#
# python exp/plot_res.py --d exp/data/ctrl_5/
# python exp/plot_res.py --d exp/data/ctrl_10/


NUM_CTRL=4
python exp/bench.py --n 20,30,40,50 --c 1 --comp baseline,multi_ctrl --parallel 0 --opt 6 --rt dqcswap --heuristic decay --wr 1 --bench pe --ctrl $NUM_CTRL --wr-path exp/data/ctrl_${NUM_CTRL}
python exp/bench.py --n 20,30,40,50 --c 1 --t 0.2 --p 0.9 --comp baseline,multi_ctrl --parallel 0 --opt 6 --rt dqcswap --heuristic decay --wr 1 --bench random --ctrl $NUM_CTRL --wr-path exp/data/ctrl_${NUM_CTRL}
python exp/bench.py --n 12,32 --c 1 --t 0.2 --p 0.9 --comp baseline,multi_ctrl --parallel 0 --opt 6 --rt dqcswap --heuristic decay --wr 1 --bench cc --ctrl $NUM_CTRL --wr-path exp/data/ctrl_${NUM_CTRL}
python exp/plot_res.py --d exp/data/ctrl_4/
