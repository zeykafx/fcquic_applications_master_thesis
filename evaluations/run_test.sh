echo "Running latency test"
CARGO_PATH=$(which cargo)
# NUM_CLIENTS=20
# RESULT_VARS=""

sudo pkill -f "sudo ip netns exec client" && sudo pkill -f "sudo ip netns exec server"

sudo sysctl -w net.core.rmem_max=26214400
sudo sysctl -w net.core.rmem_default=26214400

# for CLIENT_ID in $(seq $NUM_CLIENTS); do
# 	RESULT_VARS="LATENCY-CLIENT${CLIENT_ID},${RESULT_VARS}"
# done
 
# # Remove the trailing comma by reversing the string, removing two chars (idk why it's 2), and reversing that again
# RESULT_VARS=$(echo ${RESULT_VARS} | rev | cut -c 2- | rev)
# echo "RESULT_VARS: ${RESULT_VARS}"


sudo -E ./venv/bin/npf-run --test ./tests/latency/script.npf \
    --single-output ./tests/latency/npf_out.csv \
    --no-graph --force-retest \
    --variables workdir=$(pwd)/.. \
    cargo_path=$CARGO_PATH \
    $@
    
# The line "$@" allows us to pass the remaning arguments from this script to the npf script
