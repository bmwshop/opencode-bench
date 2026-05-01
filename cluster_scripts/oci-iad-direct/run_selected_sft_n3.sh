#!/bin/bash
set -euo pipefail

REPO_ROOT=${REPO_ROOT:-/lustre/fsw/portfolios/llmservice/users/drekesh/code/opencode-bench}
CONFIG_DIR=${REPO_ROOT}/cluster_configs
cd "${REPO_ROOT}"

CLUSTER=${CLUSTER:-oci-iad-direct}
SOURCE_ROOT=${SOURCE_ROOT:-/lustre/fsw/portfolios/llmservice/users/smajumdar/results/opencode_paper/v1}
OUTPUT_ROOT=${OUTPUT_ROOT:-/lustre/fsw/portfolios/llmservice/users/drekesh/results/opencode_paper/v1}
WORKSPACE_MOUNT="${SOURCE_ROOT}:/workspace"

PARTITION=batch_block1,batch_block3,batch_block4
MAX_TOKENS=8192
JOBS=4
TIMEOUT=600
RETRIES=5
TRIALS=${TRIALS:-3}

# Optional:
#   DRY_RUN=1 bash cluster_scripts/oci-iad-direct/run_selected_sft_n3.sh
#   BENCHMARK_ARGS="--benchmark-id 21" bash cluster_scripts/oci-iad-direct/run_selected_sft_n3.sh
DRY_RUN=${DRY_RUN:-0}
BENCHMARK_ARGS=${BENCHMARK_ARGS:-}

RUN_NAMES=(
  "combined-v1-2-iad_qwen3_8b_msg_fmt_lr1e-05_ep1.0_gbs32"
  "combined-v1-2-iad_qwen2.5_14b_instruct_reasoning_msg_fmt_lr1e-05_ep1.0_gbs32"
)

COMMON_ARGS=()
if [[ "${DRY_RUN}" == "1" ]]; then
  COMMON_ARGS+=(--dry-run)
fi
if [[ -n "${BENCHMARK_ARGS}" ]]; then
  # shellcheck disable=SC2206
  COMMON_ARGS+=(${BENCHMARK_ARGS})
fi

if [[ ! -d "${SOURCE_ROOT}" ]]; then
  echo "ERROR: SOURCE_ROOT does not exist: ${SOURCE_ROOT}" >&2
  exit 1
fi

mkdir -p "${OUTPUT_ROOT}"

for run_name in "${RUN_NAMES[@]}"; do
  model_dir="${SOURCE_ROOT}/${run_name}/final_hf_model"
  if [[ ! -d "${model_dir}" ]]; then
    echo "ERROR: missing checkpoint: ${model_dir}" >&2
    echo "       Set SOURCE_ROOT if this checkpoint lives in another results tree." >&2
    exit 1
  fi

  output_dir="${OUTPUT_ROOT}/${run_name}/opencode-bench-eval/"
  case "${run_name}" in
    *qwen2.5_14b*)
      server_args="--tensor-parallel-size 8 --data-parallel-size 1 --enable-auto-tool-choice --reasoning-parser qwen3 --tool-call-parser hermes"
      ;;
    *qwen3_8b*)
      server_args="--tensor-parallel-size 4 --pipeline-parallel-size 2 --enable-auto-tool-choice --reasoning-parser qwen3 --tool-call-parser hermes"
      ;;
    *)
      echo "ERROR: don't know vLLM server args for run '${run_name}'" >&2
      exit 1
      ;;
  esac

  for trial in $(seq 1 "${TRIALS}"); do
    expname=$(printf "eval-%02d" "${trial}")

    echo "=== submitting ${run_name} ${expname}/${TRIALS} on ${CLUSTER} ==="
    echo "    model:  /workspace/${run_name}/final_hf_model/"
    echo "    output: ${output_dir}${expname}"

    python "${REPO_ROOT}/run_cluster.py" \
      --cluster "${CLUSTER}" \
      --config-dir "${CONFIG_DIR}" \
      --expname "${expname}" \
      --model "/workspace/${run_name}/final_hf_model/" \
      --mount-paths "${WORKSPACE_MOUNT}" \
      --server-nodes 1 \
      --server-gpus 8 \
      --timeout "${TIMEOUT}" \
      --output-dir "${output_dir}" \
      --server-args "${server_args}" \
      --time-min "01:45:00" \
      -j "${JOBS}" \
      --retry-on-timeout "${RETRIES}" \
      --dependent-jobs 0 \
      --max-output-tokens "${MAX_TOKENS}" \
      --reuse-code \
      --skip-schema-check \
      --partition "${PARTITION}" \
      "${COMMON_ARGS[@]}"
  done
done
