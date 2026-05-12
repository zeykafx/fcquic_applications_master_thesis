# use a default topology name if no argument is provided, otherwise use the provided argument as the topo name

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $0 [TEST_DIR_NAME] [TOPO_CONF_NAME] [USE_POISSON]"
    echo ""
    echo "Arguments:"
    echo "  TEST_DIR_NAME    Test dir name (default: receivers)"
    echo "  TOPO_CONF_NAME   Topo config name (default: receivers_0%_loss)"
    echo "  USE_POISSON      Use Poisson distribution: true/false (default: true)"
    echo ""
    echo "Examples:"
    echo "  $0"
    echo "  $0 receivers receivers_0%_loss false"
    echo "  $0 latency medium_0%_loss true"
    echo "  $0 other_test other_topo true"
    exit 0
fi

# check not too many arguments are passed in
if [ $# -gt 3 ]; then
    echo "Too many arguments (got: $#, expected 3)" >&2
    exit 1
fi

# defaults
TEST_DIR_NAME="receivers"
TOPO_CONF_NAME="receivers_0%_loss"
USE_POISSON="true"
TAGS_TO_USE=""

if [ $# -ge 1 ] && [ -n "$1" ]; then
    TEST_DIR_NAME="$1"
fi

GRAPH_SCRIPT_TO_USE="$TEST_DIR_NAME"

if [ $# -ge 2 ] && [ -n "$2" ]; then
    TOPO_CONF_NAME="$2"
fi

if [ $# -ge 3 ] && [ -n "$3" ]; then
    USE_POISSON="$3"
fi

if [ "$USE_POISSON" != "true" ] && [ "$USE_POISSON" != "false" ]; then
    echo "USE_POISSON must be true or false" >&2
    exit 1
fi

POISSON_STR="poisson"
if [ "$USE_POISSON" = "false" ]; then
	POISSON_STR="uniform"
fi

if [ "$TEST_DIR_NAME" = "latency" ]; then
    TAGS_TO_USE="--tags latency"
elif [ "$TEST_DIR_NAME" = "data" ]; then
    TAGS_TO_USE="--tags data"
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
PREV_RUN_NBR_TCP_NO_TLS=$(find "${DIR}" -maxdepth 1 -type d -name '*_tcp_no_tls' -printf '%f\n' 2>/dev/null | grep -oE '^[0-9]+' | sort -n | tail -n 1)
# looking for previous fcquic run
PREV_RUN_NBR_FCQUIC_NO_FEC=$(find "${DIR}" -maxdepth 1 -type d -name '*_fcquic_no_fec' -printf '%f\n' 2>/dev/null | grep -oE '^[0-9]+' | sort -n | tail -n 1)
PREV_RUN_NBR_FCQUIC_FEC=$(find "${DIR}" -maxdepth 1 -type d -name '*_fcquic_fec' -printf '%f\n' 2>/dev/null | grep -oE '^[0-9]+' | sort -n | tail -n 1)
# looking for previous tokio-quiche run
PREV_RUN_NBR_TOKIO_QUICHE=$(find "${DIR}" -maxdepth 1 -type d -name '*_tokio_quiche' -printf '%f\n' 2>/dev/null | grep -oE '^[0-9]+' | sort -n | tail -n 1)


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

# ------------ BASELINE TCP (NO TLS) ------------

# setup tcp_no_tls logs directory
PREV_RUN_NBR_TCP_NO_TLS=${PREV_RUN_NBR_TCP_NO_TLS:-0}
CUR_RUN_TCP_NO_TLS=$(echo "${PREV_RUN_NBR_TCP_NO_TLS}+1" | bc)
LOGS_BASE_DIR_TCP_NO_TLS=${DIR}/${CUR_RUN_TCP_NO_TLS}

LOGS_BASE_DIR_TCP_NO_TLS="${LOGS_BASE_DIR_TCP_NO_TLS}_tcp_no_tls"

sudo mkdir ${LOGS_BASE_DIR_TCP_NO_TLS}
RUN_LOGS_DIR_TCP_NO_TLS=${LOGS_BASE_DIR_TCP_NO_TLS}
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

# ------------ TOKIO-QUICHE ------------
PREV_RUN_NBR_TOKIO_QUICHE=${PREV_RUN_NBR_TOKIO_QUICHE:-0}
CUR_RUN_TOKIO_QUICHE=$(echo "${PREV_RUN_NBR_TOKIO_QUICHE}+1" | bc)
LOGS_BASE_DIR_TOKIO_QUICHE=${DIR}/${CUR_RUN_TOKIO_QUICHE}

LOGS_BASE_DIR_TOKIO_QUICHE="${LOGS_BASE_DIR_TOKIO_QUICHE}_tokio_quiche"

sudo mkdir ${LOGS_BASE_DIR_TOKIO_QUICHE}
RUN_LOGS_DIR_TOKIO_QUICHE=${LOGS_BASE_DIR_TOKIO_QUICHE}

echo "RUN_LOGS_DIR_BASELINE=${LOGS_BASE_DIR_BASELINE}"
echo "RUN_LOGS_DIR_TCP=${LOGS_BASE_DIR_TCP}"
echo "RUN_LOGS_DIR_TCP_NO_TLS=${LOGS_BASE_DIR_TCP_NO_TLS}"
echo "RUN_LOGS_DIR_FCQUIC_NO_FEC=${LOGS_BASE_DIR_FCQUIC_NO_FEC}"
echo "RUN_LOGS_DIR_FCQUIC_FEC=${LOGS_BASE_DIR_FCQUIC_FEC}"
echo "RUN_LOGS_DIR_TOKIO_QUICHE=${LOGS_BASE_DIR_TOKIO_QUICHE}"

# Give every use permission to read and write files in the logs folder
# It's annoying otherwise to have to move files as root
sudo chmod -R 777 ./$DIR

cd $WORKDIR/evaluations

# ---------------- Topology setup ----------------

cd $WORKDIR/evaluations/topologies

echo "Setting up the topology"

OUTPUT=$(sudo python3 ./create-topo.py ./configs/${TEST_DIR_NAME}/${TOPO_CONF_NAME}.yaml setup)
# read the topology file to figure out the number of clients in the topo
NUM_CLIENTS=$(echo "$OUTPUT" | grep "number_of_clients=" | sed 's/number_of_clients=//')


echo "Set up topologies, now waiting for convergence"

# code from https://github.com/Aperence/FFSexp3-master-thesis/blob/57364d1b4244bb2c1c259dd4c41047670ab82b9a/evaluation/npfs/experiment.npf//L74

CLIENT_ID_CONVERGENCE_TEST=1
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
sleep 5

# ---------------- Running npf script ----------------

cd $WORKDIR/evaluations

# Override the number of clients only for the lantency test, this is because the other tests use a varying number of clients
# whereas the latency test always uses the all of clients defined in the topology file
# so for this test only we grep the numher of clients in the topo and override the value in the npf script
# That way i don't have to hardcode the number of clients (because i forget to change it...)
NUM_CLIENTS_OVERRIDE_ARG=""
if [ "$TEST_DIR_NAME" = "latency" ]; then
    NUM_CLIENTS_OVERRIDE_ARG="NUM_CLIENTS=$NUM_CLIENTS"
    
    echo "Overriding the number of clients to be $NUM_CLIENTS, as given by the topology script"
fi


sudo -E ./venv/bin/npf-run --test ./tests/script.npf \
    --single-output ./tests/${TEST_DIR_NAME}/out/${RESULT_FILENAME}.csv \
    --no-graph --force-retest ${TAGS_TO_USE} \
    --variables WORKDIR=$WORKDIR \
    RUN_LOGS_DIR_FCQUIC_NO_FEC=$RUN_LOGS_DIR_FCQUIC_NO_FEC \
    RUN_LOGS_DIR_FCQUIC_FEC=$RUN_LOGS_DIR_FCQUIC_FEC \
    RUN_LOGS_DIR_BASELINE=$RUN_LOGS_DIR_BASELINE \
    RUN_LOGS_DIR_TCP=$RUN_LOGS_DIR_TCP \
    RUN_LOGS_DIR_TCP_NO_TLS=$RUN_LOGS_DIR_TCP_NO_TLS \
    RUN_LOGS_DIR_TOKIO_QUICHE=$RUN_LOGS_DIR_TOKIO_QUICHE \
    CARGO_PATH=$CARGO_PATH \
    TEST_DIR_NAME=$TEST_DIR_NAME \
    TOPO_CONF_NAME=$TOPO_CONF_NAME \
    POISSON="$USE_POISSON" \
    $NUM_CLIENTS_OVERRIDE_ARG

# give permissions to all users to read and write the output file.
# otherwise if this wasn't done, we'd need to use sudo to move remove or rename the output file
sudo chmod 777 ./tests/${TEST_DIR_NAME}/out/${RESULT_FILENAME}.csv

# ---------------- Plots ----------------

echo "Graphing results"


cd $WORKDIR/evaluations/graphs

# ADD_ARGS=""
# if [ "$TEST_DIR_NAME" = "latency" ]; then
#     ADD_ARGS="--inset"
# fi
# ./${GRAPH_SCRIPT_TO_USE}.py ../tests/${TEST_DIR_NAME}/out/${RESULT_FILENAME}.csv ./${TEST_DIR_NAME} ${ADD_ARGS}

echo "Plots written"

# ---------------- Tearing down the topology ----------------

cd $WORKDIR/evaluations/topologies

echo "Tearing down the topology ${TOPO_CONF_NAME}"
sudo python3 ./create-topo.py ./configs/${TEST_DIR_NAME}/${TOPO_CONF_NAME}.yaml teardown

echo "Done tearing down the topology"
