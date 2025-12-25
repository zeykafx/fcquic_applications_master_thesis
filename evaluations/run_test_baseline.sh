# echo "Running latency test with BASELINE QUIC version"
# CARGO_PATH=$(which cargo)

# # Killing any server or client application still running
# sudo pkill -f "sudo ip netns exec client" && sudo pkill -f "sudo ip netns exec server"

# sudo -E ./venv/bin/npf-run --test ./tests/latency/script.npf \
#     --single-output ./tests/latency/out/npf_out_baseline.csv \
#     --no-graph --force-retest \
#     --variables workdir=$(pwd)/.. \
#     IS_BASELINE=true \
#     cargo_path=$CARGO_PATH \
#     $@

# # The line "$@" allows us to pass the remaning arguments from this script to the npf script

./run_test.sh true
