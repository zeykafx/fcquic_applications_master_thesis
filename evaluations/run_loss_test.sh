#!/bin/bash

declare -A TEST_TOPOS

TEST_TOPOS[latency]="
    solo_10gbps
    tiny_100mbps
    small_0%_loss_1000mbps
    small_0_1%_loss_1000mbps
    small_0_5%_loss_1000mbps
    small_5%_loss_1000mbps
    small_10%_loss_1000mbps
    medium_0%_loss
    medium_1%_loss
    medium_5%_loss
"

TEST_TOPOS[receivers]="
    receivers
"

TEST_TOPOS[data]="
    data
"

for key in latency receivers data; do
    for topo in ${TEST_TOPOS[$key]}; do
        echo "Running tests for [${key}] topo ${topo}"
        ./run_test.sh "${key}" "${topo}" true
        echo ""
    done
done
