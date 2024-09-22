#!/bin/zsh



# Function to execute commands
execute_command() {
    local description="$1"
    local cmd="$2"

    echo "----------------------------------------"
    echo "Executing: $description"
    echo "Command: $cmd"
    echo "----------------------------------------"

    eval "$cmd"
    if [ $? -ne 0 ]; then
        echo "$description execution failed, script terminated."
        exit 1
    fi
}

# Define command parameters
N_VALUES="10,20,30"
C_VALUE=10
PARALLEL=1
RT="dqcswap"
P_VALUE=0.9
T_VALUE=0.2

# Execute all commands
execute_command "Baseline comparison experiment" "python exp/bench.py --n $N_VALUES --c $C_VALUE --parallel $PARALLEL --comp baseline --opt 3 --t $T_VALUE --p $P_VALUE --rt $RT --heuristic dqcmap --wr 1"
execute_command "Multi-controller comparison experiment - decay" "python exp/bench.py --n $N_VALUES --c $C_VALUE --parallel $PARALLEL --comp multi_ctrl --opt 3 --t $T_VALUE --p $P_VALUE --rt $RT --heuristic decay --wr 1"
execute_command "Multi-controller comparison experiment - dqcmap" "python exp/bench.py --n $N_VALUES --c $C_VALUE --parallel $PARALLEL --comp multi_ctrl --opt 3 --t $T_VALUE --p $P_VALUE --rt $RT --heuristic dqcmap --wr 1"
execute_command "Multi-controller optimization 6 - decay" "python exp/bench.py --n $N_VALUES --c $C_VALUE --parallel $PARALLEL --comp multi_ctrl --opt 6 --t $T_VALUE --p $P_VALUE --rt $RT --heuristic decay --wr 1"
execute_command "Multi-controller optimization 6 - dqcmap" "python exp/bench.py --n $N_VALUES --c $C_VALUE --parallel $PARALLEL --comp multi_ctrl --opt 6 --t $T_VALUE --p $P_VALUE --rt $RT --heuristic dqcmap --wr 1"
execute_command "Plot results" "python exp/plot_res.py"

echo "All commands have been successfully executed."
