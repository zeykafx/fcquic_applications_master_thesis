IS_BASELINE=${1:-false} # set IS_BASELINE to true if the first arg is true, otherwise set it to false

# https://stackoverflow.com/a/13864829
if [ -z "${1+x}" ]; then
	# no arg is passed, do nothing
	echo "No arg passed in, running fcquic version"
else
	shift # remove the first argument from the list
fi

CARGO_PATH=$(which cargo)
workdir=$(pwd)/..
RESULT_FILENAME="npf_out"

if [ "$IS_BASELINE" = "true" ]; then
    echo "Running latency test with BASELINE QUIC version"
else
    echo "Running latency test"
fi

# Killing any server or client application still running
sudo pkill -f "sudo ip netns exec client" && sudo pkill -f "sudo ip netns exec server"

# ---------------- Logs setup ----------------
echo "Setting up logs directory"

cd $workdir/evaluations/tests/latency

sudo mkdir ./logs 2> /dev/null
DIR=./logs

# PREV_RUN_NBR=$(find ${DIR} -maxdepth 1 -type d -regex '.*/[0-9]+' -printf '%f\n' 2>/dev/null | sort -n | tail -n 1)
# PREV_RUN_NBR=$(find ${DIR} -maxdepth 1 -type d -name '[0-9]*' -printf '%f\n' 2>/dev/null | grep -oE '^[0-9]+' | sort -n | tail -n 1)
if [ "$IS_BASELINE" = "true" ]; then
    # looking for previous fcquic run
    PREV_RUN_NBR=$(find "${DIR}" -maxdepth 1 -type d -name '*_fcquic' -printf '%f\n' 2>/dev/null | grep -oE '^[0-9]+' | sort -n | tail -n 1)
else
    # looking for previous baseline run
    PREV_RUN_NBR=$(find "${DIR}" -maxdepth 1 -type d -name '*_baseline' -printf '%f\n' 2>/dev/null | grep -oE '^[0-9]+' | sort -n | tail -n 1)
fi

PREV_RUN_NBR=${PREV_RUN_NBR:-0}
CUR_RUN=$(echo "${PREV_RUN_NBR}+1" | bc)
LOGS_BASE_DIR=${DIR}/${CUR_RUN}

# append "baseline" to the dir name if running the baseline test
if [ "$IS_BASELINE" = "true" ]; then
	LOGS_BASE_DIR="${LOGS_BASE_DIR}_baseline"
    RESULT_FILENAME="${RESULT_FILENAME}_baseline"
else
	LOGS_BASE_DIR="${LOGS_BASE_DIR}_fcquic"
fi

sudo mkdir ${LOGS_BASE_DIR}
RUN_LOGS_DIR=${LOGS_BASE_DIR}

cd $workdir/evaluations

# ---------------- Running npf script ----------------

sudo -E ./venv/bin/npf-run --test ./tests/latency/script.npf \
    --single-output ./tests/latency/out/${RESULT_FILENAME}.csv \
    --no-graph --force-retest \
    --variables workdir=$workdir \
    cargo_path=$CARGO_PATH \
    RUN_LOGS_DIR=$RUN_LOGS_DIR \
    IS_BASELINE=$IS_BASELINE \
    $@

# The line "$@" allows us to pass the remaning arguments from this script to the npf script
