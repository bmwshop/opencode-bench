# Running on a Cluster

`run_cluster.py` submits opencode-bench evaluation jobs to a Slurm cluster via the [NeMo-Skills](https://github.com/NVIDIA/NeMo-Skills) `run_cmd` API. It launches a vLLM server as a sidecar, installs the opencode CLI, and runs the full benchmark pipeline (`run.py` + `eval.py`) inside a container.

## Prerequisites

- Python 3.10+
- NeMo-Skills installed or on `PYTHONPATH`
- A cluster config YAML in `cluster_configs/` (e.g. `oci-iad.yaml`, `eos.yaml`)
- A model accessible on the cluster filesystem (e.g. `/hf_models/Qwen/Qwen2.5-32B-Instruct`)

**Important:** NeMo-Skills packages only git-tracked files when staging code to the cluster. If you have local changes to samples, evaluators, project fixtures, or any other files, you must `git commit` them before running `run_cluster.py` -- uncommitted changes will not be present inside the container.

## Quick Start

```bash
python run_cluster.py \
  --cluster oci-iad \
  --model /hf_models/Qwen/Qwen2.5-32B-Instruct \
  --server-gpus 8 \
  --output-dir /lustre/fsw/portfolios/llmservice/users/$USER/opencode-bench-results \
  --expname qwen-32b-eval
```

Results will be written to `{output-dir}/{expname}/` (i.e. `.../opencode-bench-results/qwen-32b-eval/`).

This will:
1. Start a vLLM server with 8 GPUs serving the specified model
2. Install Node.js and the opencode CLI inside the container
3. Inject the vLLM server URL into each project's `opencode.json`
4. Run all benchmark samples via `run.py`
5. Evaluate results via `eval.py`
6. Persist results to the `--output-dir` path on the cluster

## Usage Examples

### Run a specific category

```bash
python run_cluster.py \
  --cluster oci-iad \
  --model /hf_models/Qwen/Qwen2.5-32B-Instruct \
  --server-gpus 8 \
  --output-dir /lustre/fsw/.../results \
  --benchmark-category tool_schema \
  --expname qwen-32b-tool-schema
```

### Run specific samples by ID

```bash
python run_cluster.py \
  --cluster oci-iad \
  --model /hf_models/Qwen/Qwen2.5-32B-Instruct \
  --server-gpus 8 \
  --output-dir /lustre/fsw/.../results \
  --expname qwen-32b-samples \
  --benchmark-id 1 --benchmark-id 2 --benchmark-id 3
```

### Use a pre-existing server

If the model is already hosted (no vLLM sidecar needed):

```bash
python run_cluster.py \
  --cluster oci-iad \
  --model /hf_models/Qwen/Qwen2.5-32B-Instruct \
  --server-address some-host:5000 \
  --output-dir /lustre/fsw/.../results \
  --expname qwen-32b-external
```

### Skip opencode installation

If the container already has `opencode` installed:

```bash
python run_cluster.py \
  --cluster oci-iad \
  --model /hf_models/Qwen/Qwen2.5-32B-Instruct \
  --server-gpus 8 \
  --output-dir /lustre/fsw/.../results \
  --expname qwen-32b-eval \
  --skip-opencode-install
```

### Custom opencode install command

```bash
python run_cluster.py \
  --cluster eos \
  --model /hf_models/custom/MyModel \
  --server-gpus 4 \
  --output-dir /lustre/fsw/.../results \
  --expname mymodel-eval \
  --opencode-install-cmd "npm install -g @titu1994/opencode"
```

### Custom opencode model name

By default the opencode model name is derived as `{provider}/{basename(model)}` (e.g. `vllm/Qwen2.5-32B-Instruct`). Override it when the vLLM model name differs:

```bash
python run_cluster.py \
  --cluster oci-iad \
  --model /hf_models/Qwen/Qwen2.5-32B-Instruct \
  --server-gpus 8 \
  --output-dir /lustre/fsw/.../results \
  --expname qwen-32b-nvidia \
  --opencode-model nvidia/Qwen2.5-32B-Instruct \
  --provider nvidia
```

### Dry run (validate without submitting)

```bash
python run_cluster.py \
  --cluster oci-iad \
  --model /hf_models/Qwen/Qwen2.5-32B-Instruct \
  --server-gpus 8 \
  --output-dir /tmp/test \
  --expname dry-run-test \
  --dry-run
```

### Additional mount paths

Mount extra directories into the container (e.g. datasets, custom configs):

```bash
python run_cluster.py \
  --cluster oci-iad \
  --model /hf_models/Qwen/Qwen2.5-32B-Instruct \
  --server-gpus 8 \
  --output-dir /lustre/fsw/.../results \
  --expname qwen-32b-eval \
  --mount-paths /lustre/fsw/.../data:/data,/lustre/fsw/.../configs:/configs
```

### Dependent jobs

Queue multiple sequential jobs (e.g. for long-running benchmarks that exceed the time limit):

```bash
python run_cluster.py \
  --cluster oci-iad \
  --model /hf_models/Qwen/Qwen2.5-32B-Instruct \
  --server-gpus 8 \
  --output-dir /lustre/fsw/.../results \
  --expname qwen-32b-long \
  --dependent-jobs 2 \
  --time-min 04:00:00
```

## Arguments Reference

### Cluster

| Flag | Default | Description |
|---|---|---|
| `--cluster` | *(required)* | Cluster config name (YAML in `cluster_configs/` or `NEMO_SKILLS_CONFIG_DIR`) |
| `--config-dir` | `None` | Custom directory to search for cluster configs |
| `--container` | `nemo-skills` | Container key from cluster config |
| `--expname` | *(required)* | NeMo-Run experiment name (appended to `--output-dir` for the results path) |
| `--num-nodes` | `1` | Number of nodes for the main task |
| `--num-gpus` | `None` | Number of GPUs per node for the main task |
| `--partition` | `None` | Slurm partition |
| `--qos` | `None` | Slurm QoS |
| `--time-min` | `None` | Minimum Slurm job time |
| `--mount-paths` | `None` | Additional comma-separated mount paths (`src:dest`) |
| `--log-dir` | `None` | Custom location for Slurm logs |
| `--dry-run` | `false` | Validate arguments without submitting |
| `--reuse-code` | `false` | Reuse code from a previous experiment |
| `--dependent-jobs` | `0` | Number of dependent sequential jobs |

### Server (vLLM sidecar)

| Flag | Default | Description |
|---|---|---|
| `--model` | *(required)* | HF model path on the cluster filesystem |
| `--server-gpus` | `None` | GPUs for vLLM server (required unless `--server-address` is set) |
| `--server-nodes` | `1` | Nodes for the vLLM server |
| `--server-type` | `vllm` | Server type (`vllm`, `sglang`, etc.) |
| `--server-args` | `""` | Extra arguments passed to the server |
| `--server-address` | `None` | Pre-existing server `host:port` (skips sidecar launch) |

### Benchmark

| Flag | Default | Description |
|---|---|---|
| `--benchmark-id` | `None` | Run specific sample(s) by ID (repeatable) |
| `--benchmark-category` | `None` | Run samples in a category (repeatable) |
| `--timeout` | `180` | Per-sample timeout in seconds |
| `--opencode-model` | *derived* | Model name in `provider/model` format for `run.py` |
| `--provider` | `vllm` | Provider key for opencode config injection |

### Output & Installation

| Flag | Default | Description |
|---|---|---|
| `--output-dir` | *(required)* | Cluster path for results (mounted to `/results` in container) |
| `--opencode-install-cmd` | *Node.js + opencode* | Command to install Node.js and opencode CLI |
| `--skip-opencode-install` | `false` | Skip installation (assumes opencode is pre-installed) |

## How It Works

### Output directory mounting

The final results path is `{output_dir}/{expname}/`, which is mounted into the container as `/results`. The benchmark command sets `OPENCODE_BENCH_RESULTS=/results` so that `common.py` writes results directly to the mounted cluster storage instead of the default `results/` relative to the code root.

### Provider URL injection

Instead of using `run.py`'s `--proxy` flag (which requires the switchyard proxy codebase), `run_cluster.py` injects the vLLM server URL directly into each project's `opencode.json` before `run.py` takes file snapshots. This sets `provider.{provider}.options.baseURL` so that the opencode CLI connects to the vLLM server.

### Node.js + opencode installation

The default installation command is run on a single rank per node before the main job:

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
apt-get install -y nodejs && \
npm install -g @anthropic/opencode
```

Override with `--opencode-install-cmd` or skip entirely with `--skip-opencode-install`.

### vLLM server lifecycle

When `--server-gpus` is set, `run_cmd` starts a vLLM server as a heterogeneous Slurm job component. The main benchmark command automatically waits (via a curl polling loop) for the server to become available at `localhost:5000` before running `run.py`.

When `--server-address` is set, no sidecar is launched and the benchmark connects to the specified external server.

## Cluster Configs

Cluster config YAMLs live in `cluster_configs/`. Each defines the executor type, container images, mounts, environment variables, and Slurm settings. See the existing configs for examples:

- `local.yaml` -- local Docker execution
- `eos.yaml` -- NVIDIA EOS cluster
- `oci-iad.yaml` -- Oracle Cloud Infrastructure (IAD)
- `oci-ord.yaml` -- Oracle Cloud Infrastructure (ORD)
