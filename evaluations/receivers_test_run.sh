
# use a default topology name if no argument is provided, otherwise use the provided argument as the topo name
TEST_DIR_NAME="receivers"
TOPO_CONF_NAME="receivers_0%_loss"
USE_POISSON="false"
if [ $# -gt 0 ]; then
	TOPO_CONF_NAME="$1"
	USE_POISSON="$2"
fi

POISSON_STR="poisson"
if [ "$USE_POISSON" = "false" ]; then
	POISSON_STR="uniform"
fi


echo "Running tests for topology: ${TEST_DIR_NAME}/${TOPO_CONF_NAME}, Sending with: ${POISSON_STR}"

CARGO_PATH=$(which cargo)
WORKDIR=$(pwd)/..
RESULT_FILENAME="npf_out_${TOPO_CONF_NAME}_${POISSON_STR}"

# Killing any server or client application still running
sudo pkill -f "sudo ip netns exec client" && sudo pkill -f "sudo ip netns exec server"

# ------------------------ Logs setup ------------------------
echo "Setting up logs directory"

cd $WORKDIR/evaluations/tests/${TEST_DIR_NAME}

sudo mkdir ./logs 2> /dev/null
DIR=./logs

# looking for previous baseline run
PREV_RUN_NBR_BASELINE=$(find "${DIR}" -maxdepth 1 -type d -name '*_baseline' -printf '%f\n' 2>/dev/null | grep -oE '^[0-9]+' | sort -n | tail -n 1)
PREV_RUN_NBR_TCP=$(find "${DIR}" -maxdepth 1 -type d -name '*_tcp' -printf '%f\n' 2>/dev/null | grep -oE '^[0-9]+' | sort -n | tail -n 1)
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


# ------------ BASELINE TCP ------------

# setup tcp logs directory
PREV_RUN_NBR_TCP=${PREV_RUN_NBR_TCP:-0}
CUR_RUN_TCP=$(echo "${PREV_RUN_NBR_TCP}+1" | bc)
LOGS_BASE_DIR_TCP=${DIR}/${CUR_RUN_TCP}

LOGS_BASE_DIR_TCP="${LOGS_BASE_DIR_TCP}_tcp"

sudo mkdir ${LOGS_BASE_DIR_TCP}
RUN_LOGS_DIR_TCP=${LOGS_BASE_DIR_TCP}

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
echo "RUN_LOGS_DIR_TCP=${LOGS_BASE_DIR_TCP}"
echo "RUN_LOGS_DIR_FCQUIC_NO_FEC=${LOGS_BASE_DIR_FCQUIC_NO_FEC}"
echo "RUN_LOGS_DIR_FCQUIC_FEC=${LOGS_BASE_DIR_FCQUIC_FEC}"

cd $WORKDIR/evaluations

# ---------------- Topology setup ----------------

cd $WORKDIR/evaluations/topologies

echo "Setting up the topology"

sudo python3 ./create-topo.py ./configs/${TEST_DIR_NAME}/${TOPO_CONF_NAME}.yaml setup

echo "Set up topologies, now waiting for convergence"

# code from https://github.com/Aperence/FFSexp3-master-thesis/blob/57364d1b4244bb2c1c259dd4c41047670ab82b9a/evaluation/npfs/experiment.npf//L74

CLIENT_ID_CONVERGENCE_TEST=2
echo "Testing convergence from client${CLIENT_ID_CONVERGENCE_TEST}"

converged=false
while [ $converged != "true" ]; do
    ping_res=$(sudo ip netns exec client${CLIENT_ID_CONVERGENCE_TEST} ping 10.10.0.2 -i 0.1 -c 5)
    errors=$(echo "$ping_res" | grep 'error')
    losses=$(echo "$ping_res" | grep 'packet loss' | cut -f6 -d' ')
    losses=${losses%\%}
    if [ -z "$errors" -a "$losses" -lt 5 ]; then
        converged=true
    else
        echo "Waiting for convergence"
    fi
done

echo "Topology setup and IS-IS converged"

# wait even more for everything to converge
sleep 10

# ---------------- Running npf script ----------------

cd $WORKDIR/evaluations

sudo -E ./venv/bin/npf-run --test ./tests/${TEST_DIR_NAME}/script.npf \
    --single-output ./tests/${TEST_DIR_NAME}/out/${RESULT_FILENAME}.csv \
    --no-graph --force-retest \
    --variables WORKDIR=$WORKDIR \
    RUN_LOGS_DIR_FCQUIC_NO_FEC=$RUN_LOGS_DIR_FCQUIC_NO_FEC \
    RUN_LOGS_DIR_FCQUIC_FEC=$RUN_LOGS_DIR_FCQUIC_FEC \
    RUN_LOGS_DIR_BASELINE=$RUN_LOGS_DIR_BASELINE \
    RUN_LOGS_DIR_TCP=$RUN_LOGS_DIR_TCP \
    CARGO_PATH=$CARGO_PATH \
    TEST_DIR_NAME=$TEST_DIR_NAME \
    TOPO_CONF_NAME=$TOPO_CONF_NAME \
    POISSON="$USE_POISSON"



# ---------------- Plots ----------------

echo "Graphing results"


cd $WORKDIR/evaluations/graphs

./receivers_cdf.py ../tests/${TEST_DIR_NAME}/out/${RESULT_FILENAME}.csv ./

echo "Plots written"

# ---------------- Tearing down the topology ----------------

cd $WORKDIR/evaluations/topologies

echo "Tearing down the topology ${TOPO_CONF_NAME}"
sudo python3 ./create-topo.py ./configs/${TEST_DIR_NAME}/${TOPO_CONF_NAME}.yaml teardown

echo "Done tearing down the topology"
