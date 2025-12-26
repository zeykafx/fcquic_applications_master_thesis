
# use a default topology name if no argument is provided, otherwise use the provided argument as the topo name
TOPO_CONF_NAME="medium_0%_loss"
if [ $# -gt 0 ]; then
	TOPO_CONF_NAME="$1"
fi

echo "Running tests for topology: ${TOPO_CONF_NAME}"

CARGO_PATH=$(which cargo)
WORKDIR=$(pwd)/..
RESULT_FILENAME="npf_out"

# Killing any server or client application still running
sudo pkill -f "sudo ip netns exec client" && sudo pkill -f "sudo ip netns exec server"
# ------------------------ Logs setup ------------------------

echo "Setting up logs directory"

cd $WORKDIR/evaluations/tests/latency

sudo mkdir ./logs 2> /dev/null
DIR=./logs

# looking for previous baseline run
PREV_RUN_NBR_BASELINE=$(find "${DIR}" -maxdepth 1 -type d -name '*_baseline' -printf '%f\n' 2>/dev/null | grep -oE '^[0-9]+' | sort -n | tail -n 1)
# looking for previous fcquic run
PREV_RUN_NBR_FCQUIC_NO_FEC=$(find "${DIR}" -maxdepth 1 -type d -name '*_fcquic_no_fec' -printf '%f\n' 2>/dev/null | grep -oE '^[0-9]+' | sort -n | tail -n 1)
PREV_RUN_NBR_FCQUIC_FEC=$(find "${DIR}" -maxdepth 1 -type d -name '*_fcquic_fec' -printf '%f\n' 2>/dev/null | grep -oE '^[0-9]+' | sort -n | tail -n 1)


# ------------ BASELINE QUIC ------------

# setup baseline logs directory
PREV_RUN_NBR_BASELINE=${PREV_RUN_NBR_BASELINE:-0}
CUR_RUN_BASELINE=$(echo "${PREV_RUN_NBR_BASELINE}+1" | bc)
LOGS_BASE_DIR_BASELINE=${DIR}/${CUR_RUN_BASELINE}

LOGS_BASE_DIR_BASELINE="${LOGS_BASE_DIR_BASELINE}_baseline"

sudo mkdir ${LOGS_BASE_DIR_BASELINE}
RUN_LOGS_DIR_BASELINE=${LOGS_BASE_DIR_BASELINE}

# ------------ FCQUIC NO FEC ------------

# Setup fcquic logs directory
PREV_RUN_NBR_FCQUIC_NO_FEC=${PREV_RUN_NBR_FCQUIC_NO_FEC:-0}
CUR_RUN_FCQUIC_NO_FEC=$(echo "${PREV_RUN_NBR_FCQUIC_NO_FEC}+1" | bc)
LOGS_BASE_DIR_FCQUIC_NO_FEC=${DIR}/${CUR_RUN_FCQUIC_NO_FEC}

LOGS_BASE_DIR_FCQUIC_NO_FEC="${LOGS_BASE_DIR_FCQUIC_NO_FEC}_fcquic_no_fec"

sudo mkdir ${LOGS_BASE_DIR_FCQUIC_NO_FEC}
RUN_LOGS_DIR_FCQUIC_NO_FEC=${LOGS_BASE_DIR_FCQUIC_NO_FEC}

# ------------ FCQUIC WITH FEC ------------
PREV_RUN_NBR_FCQUIC_FEC=${PREV_RUN_NBR_FCQUIC_FEC:-0}
CUR_RUN_FCQUIC_FEC=$(echo "${PREV_RUN_NBR_FCQUIC_FEC}+1" | bc)
LOGS_BASE_DIR_FCQUIC_FEC=${DIR}/${CUR_RUN_FCQUIC_FEC}

LOGS_BASE_DIR_FCQUIC_FEC="${LOGS_BASE_DIR_FCQUIC_FEC}_fcquic_fec"

sudo mkdir ${LOGS_BASE_DIR_FCQUIC_FEC}
RUN_LOGS_DIR_FCQUIC_FEC=${LOGS_BASE_DIR_FCQUIC_FEC}

echo "RUN_LOGS_DIR_BASELINE=${LOGS_BASE_DIR_BASELINE}"
echo "RUN_LOGS_DIR_FCQUIC_NO_FEC=${LOGS_BASE_DIR_FCQUIC_NO_FEC}"
echo "RUN_LOGS_DIR_FCQUIC_FEC=${LOGS_BASE_DIR_FCQUIC_FEC}"

cd $WORKDIR/evaluations

# ---------------- Running npf script ----------------

sudo -E ./venv/bin/npf-run --test ./tests/latency/script.npf \
    --single-output ./tests/latency/out/${RESULT_FILENAME}.csv \
    --no-graph --force-retest \
    --variables WORKDIR=$WORKDIR \
    RUN_LOGS_DIR_FCQUIC_NO_FEC=$RUN_LOGS_DIR_FCQUIC_NO_FEC \
    RUN_LOGS_DIR_FCQUIC_FEC=$RUN_LOGS_DIR_FCQUIC_FEC \
    RUN_LOGS_DIR_BASELINE=$RUN_LOGS_DIR_BASELINE \
    CARGO_PATH=$CARGO_PATH \
    TOPO_CONF_NAME=$TOPO_CONF_NAME


# The line "$@" allows us to pass the remaning arguments from this script to the npf script

# ---------------- Plots ----------------

echo "Graphing results"

cd $WORKDIR/evaluations/tests/latency/graphs

./cdf_plots.py ../out/npf_out.csv

echo "Plots written"
