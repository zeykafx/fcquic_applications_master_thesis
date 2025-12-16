echo "Running latency test"

./venv/bin/npf-run --test ./tests/latency/script.npf \
    --single-output ./tests/latency/npf_out.csv \
    --no-graph --force-retest \
    --variables workdir=$(pwd)/.. \
    cargo_path="/home/corentin/.cargo/bin/cargo"
