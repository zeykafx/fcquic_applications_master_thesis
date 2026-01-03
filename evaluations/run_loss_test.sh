#!/bin/bash

MEDIUM_TOPOLOGIES=(
    "medium_0%_loss"
    "medium_0_1%_loss"
    "medium_0_5%_loss"
    "medium_1%_loss"
    "medium_1_5%_loss"
    "medium_2%_loss"
    "medium_3%_loss"
    "medium_4%_loss"
    "medium_5%_loss"
    "medium_7_5%_loss"
    "medium_10%_loss"
)

for topo in "${MEDIUM_TOPOLOGIES[@]}"; do
    echo "Running tests for topo ${topo}"

    echo "Running with uniform distribution..."
    ./run_test.sh latency "${topo}" false

    echo "Running with Poisson distribution..."
    ./run_test.sh latency "${topo}" true

    echo ""
done
