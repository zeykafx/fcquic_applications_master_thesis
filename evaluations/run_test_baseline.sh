echo "Running latency test with BASELINE QUIC version"
CARGO_PATH=$(which cargo)

sudo -E ./venv/bin/npf-run --test ./tests/latency/script.npf \
    --single-output ./tests/latency/out/npf_out_baseline.csv \
    --no-graph --force-retest \
    --variables workdir=$(pwd)/.. \
    IS_BASELINE=true \
    cargo_path=$CARGO_PATH \
    $@

# The line "$@" allows us to pass the remaning arguments from this script to the npf script
