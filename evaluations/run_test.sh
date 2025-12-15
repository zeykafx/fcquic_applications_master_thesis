echo "Running latency test"

npf-run --test ./tests/latency/script.npf --cluster client=localhost server=localhost --single-output ./tests/latency/npf_out.csv --no-graph