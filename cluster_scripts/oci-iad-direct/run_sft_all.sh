#!/bin/bash
set -euo pipefail
shopt -s nullglob

REPO_ROOT=${REPO_ROOT:-/lustre/fsw/portfolios/llmservice/users/drekesh/code/opencode-bench}
CONFIG_DIR=${REPO_ROOT}/cluster_configs
cd "${REPO_ROOT}"

CLUSTER=${CLUSTER:-oci-iad-direct}
SOURCE_ROOT=${SOURCE_ROOT:-/lustre/fsw/portfolios/llmservice/users/smajumdar/results/opencode_paper/v1}
OUTPUT_ROOT=${OUTPUT_ROOT:-/lustre/fsw/portfolios/llmservice/users/drekesh/results/opencode_paper/v1}
WORKSPACE_MOUNT="${SOURCE_ROOT}:/workspace"

# Optional:
#   DRY_RUN=1 bash cluster_scripts/oci-iad-direct/run_sft_all.sh
#   BENCHMARK_ARGS="--benchmark-id 21" bash cluster_scripts/oci-iad-direct/run_sft_all.sh
#   RUN_FILTER="qwen2.5_7b" bash cluster_scripts/oci-iad-direct/run_sft_all.sh
DRY_RUN=${DRY_RUN:-0}
BENCHMARK_ARGS=${BENCHMARK_ARGS:-}
RUN_FILTER=${RUN_FILTER:-}

COMMON_ARGS=()
if [[ "${DRY_RUN}" == "1" ]]; then
  COMMON_ARGS+=(--dry-run)
fi
if [[ -n "${BENCHMARK_ARGS}" ]]; then
  # shellcheck disable=SC2206
  COMMON_ARGS+=(${BENCHMARK_ARGS})
fi

server_args_for_run() {
  local run_name=$1

  case "${run_name}" in
    *qwen2.5_7b*)
      echo "--tensor-parallel-size 4 --pipeline-parallel-size 2 --enable-auto-tool-choice --reasoning-parser qwen3 --tool-call-parser hermes"
      ;;
    *qwen2.5_14b*)
      echo "--tensor-parallel-size 8 --data-parallel-size 1 --enable-auto-tool-choice --reasoning-parser qwen3 --tool-call-parser hermes"
      ;;
    *qwen3_8b*)
      echo "--tensor-parallel-size 4 --pipeline-parallel-size 2 --enable-auto-tool-choice --reasoning-parser qwen3 --tool-call-parser hermes"
      ;;
    *qwen3_30b_a3b*)
      echo "--tensor-parallel-size 1 --data-parallel-size 8 --enable-expert-parallel --enable-auto-tool-choice --reasoning-parser qwen3 --tool-call-parser hermes"
      ;;
    *)
      echo "ERROR: don't know vLLM server args for run '${run_name}'" >&2
      return 1
      ;;
  esac
}

if [[ ! -d "${SOURCE_ROOT}" ]]; then
  echo "ERROR: SOURCE_ROOT does not exist: ${SOURCE_ROOT}" >&2
  exit 1
fi

mkdir -p "${OUTPUT_ROOT}"

for model_dir in "${SOURCE_ROOT}"/*/final_hf_model; do
  run_dir=$(dirname "${model_dir}")
  run_name=$(basename "${run_dir}")

  if [[ -n "${RUN_FILTER}" && "${run_name}" != *"${RUN_FILTER}"* ]]; then
    continue
  fi

  server_args=$(server_args_for_run "${run_name}")
  output_dir="${OUTPUT_ROOT}/${run_name}/opencode-bench-eval/"

  echo "=== submitting ${run_name} on ${CLUSTER} ==="
  echo "    model:  /workspace/${run_name}/final_hf_model/"
  echo "    output: ${output_dir}"

  python "${REPO_ROOT}/run_cluster.py" \
    --cluster "${CLUSTER}" \
    --config-dir "${CONFIG_DIR}" \
    --expname eval \
    --model "/workspace/${run_name}/final_hf_model/" \
    --mount-paths "${WORKSPACE_MOUNT}" \
    --server-nodes 1 \
    --server-gpus 8 \
    --timeout 600 \
    --output-dir "${output_dir}" \
    --server-args "${server_args}" \
    --time-min "01:45:00" \
    -j 4 \
    --retry-on-timeout 5 \
    --dependent-jobs 0 \
    --max-output-tokens 8192 \
    --reuse-code \
    --skip-schema-check \
    "${COMMON_ARGS[@]}"
done
