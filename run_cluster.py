#!/usr/bin/env python3
"""
Launch opencode-bench evaluation on a Slurm cluster via NeMo-Skills.

This script:
1. Starts a vLLM server on cluster GPUs (or connects to an existing one)
2. Installs Node.js + the opencode CLI (unless skipped)
3. Injects the vLLM server URL into each project's opencode.json config
4. Runs the opencode-bench benchmark (run.py + eval.py)
5. Persists results to the mounted output directory

Uses NeMo-Skills' run_cmd API for cluster job management, container
orchestration, and vLLM server sidecar hosting.

Usage:
    python run_cluster.py \\
        --cluster oci-iad \\
        --model /hf_models/Qwen/Qwen2.5-32B-Instruct \\
        --server-gpus 8 \\
        --output-dir /lustre/fsw/.../opencode-bench-results

    python run_cluster.py \\
        --cluster oci-iad \\
        --model /hf_models/Qwen/Qwen2.5-32B-Instruct \\
        --server-address some-host:5000 \\
        --output-dir /lustre/fsw/.../results

    python run_cluster.py ... --dry-run   # validate without submitting
"""

import argparse
import os
import sys

try:
    from nemo_skills.pipeline.run_cmd import run_cmd
    from nemo_skills.pipeline.cli import wrap_arguments
    from nemo_skills.pipeline.utils import get_cluster_config, create_remote_directory, get_mounted_path, resolve_mount_paths
except ImportError:
    print(
        "Error: NeMo-Skills is not installed or not in PYTHONPATH.\n"
        "Please ensure the NeMo-Skills repository is accessible.\n"
        "You can set PYTHONPATH like: export PYTHONPATH=/path/to/NeMo-Skills:$PYTHONPATH"
    )
    sys.exit(1)

os.environ["NEMO_SKILLS_DISABLE_UNCOMMITTED_CHANGES_CHECK"] = "1"

# ---------------------------------------------------------------------------
# opencode CLI install command
# ---------------------------------------------------------------------------
#
# The official opencode installer (https://opencode.ai/install) resolves the
# latest release by calling the unauthenticated GitHub REST API
# (https://api.github.com/repos/anomalyco/opencode/releases/latest). Compute
# nodes on shared clusters typically egress through a single NAT IP, and that
# IP frequently blows past GitHub's 60 req/hr/IP unauthenticated rate limit,
# causing the installer to fail with a misleading:
#
#     Failed to fetch version information
#
# (the underlying response is actually HTTP 403 "API rate limit exceeded").
#
# To make installs robust, we first try the latest release, and if that
# fails we fall back to a pinned version. Passing --version makes the
# installer skip the api.github.com call entirely and fetch the release
# asset directly from github.com/releases/download/..., which is not
# subject to the REST API rate limit.
#
# Bump PINNED_OPENCODE_VERSION periodically; get the current value from
# https://github.com/anomalyco/opencode/releases/latest.
PINNED_OPENCODE_VERSION = "1.4.11"

DEFAULT_INSTALL_CMD = (
    "("
    "curl -fsSL https://opencode.ai/install | bash -s -- --no-modify-path"
    ") || ("
    "echo 'opencode latest install failed, falling back to pinned "
    f"v{PINNED_OPENCODE_VERSION}' >&2 && "
    "curl -fsSL https://opencode.ai/install | bash -s -- --no-modify-path "
    f"--version {PINNED_OPENCODE_VERSION}"
    ") && "
    "ln -sf $HOME/.opencode/bin/opencode /usr/local/bin/opencode"
)

DEFAULT_SERVER_PORT = 5000



# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        description="Launch opencode-bench evaluation on a Slurm cluster",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # -- Cluster ---------------------------------------------------------
    cluster = parser.add_argument_group("Cluster")
    cluster.add_argument(
        "--cluster", required=True,
        help="Cluster config name (matches a YAML in cluster_configs/ or NEMO_SKILLS_CONFIG_DIR)",
    )
    cluster.add_argument("--config-dir", default=None, help="Custom directory to search for cluster configs")
    cluster.add_argument("--container", default="nemo-skills", help="Container key from cluster config")
    cluster.add_argument("--expname", required=True, help="NeMo-Run experiment name (appended to --output-dir for the results path)")
    cluster.add_argument("--num-nodes", type=int, default=1, help="Number of nodes for the main task")
    cluster.add_argument("--num-gpus", type=int, default=None, help="Number of GPUs per node for the main task")
    cluster.add_argument("--partition", default=None, help="Slurm partition")
    cluster.add_argument("--qos", default=None, help="Slurm QoS")
    cluster.add_argument("--time-min", default=None, help="Minimum Slurm job time")
    cluster.add_argument(
        "--mount-paths", default=None,
        help="Comma-separated additional mount paths (src:dest)",
    )
    cluster.add_argument("--log-dir", default=None, help="Custom location for Slurm logs")
    cluster.add_argument("--dry-run", action="store_true", help="Validate arguments without submitting")
    cluster.add_argument("--reuse-code", action="store_true", help="Reuse code from previous experiment")
    cluster.add_argument(
        "--dependent-jobs", type=int, default=0,
        help="Number of dependent sequential jobs (total = 1 + this value)",
    )

    # -- Server ----------------------------------------------------------
    server = parser.add_argument_group("Server (vLLM sidecar)")
    server.add_argument(
        "--model", required=True,
        help="HF model path on the cluster filesystem (e.g. /hf_models/Qwen/Qwen2.5-32B-Instruct)",
    )
    server.add_argument(
        "--server-gpus", type=int, default=None,
        help="Number of GPUs for the vLLM server (enables sidecar hosting)",
    )
    server.add_argument("--server-nodes", type=int, default=1, help="Number of nodes for the vLLM server")
    server.add_argument("--server-type", default="vllm", help="Server type (vllm, sglang, etc.)")
    server.add_argument("--server-args", default="", help="Extra arguments passed to the vLLM server")
    server.add_argument(
        "--server-address", default=None,
        help="Address of a pre-existing server (host:port). Skips vLLM sidecar launch.",
    )

    # -- Benchmark -------------------------------------------------------
    bench = parser.add_argument_group("Benchmark")
    bench.add_argument(
        "--benchmark-id", action="append", default=None,
        help="Run specific sample(s) by ID (repeatable, forwarded as --id to run.py/eval.py)",
    )
    bench.add_argument(
        "--benchmark-category", action="append", default=None,
        help="Run samples in a category (repeatable, forwarded as --category)",
    )
    bench.add_argument("--timeout", type=int, default=180, help="Per-sample timeout in seconds")
    bench.add_argument(
        "--opencode-model", default=None,
        help="Model name in provider/model format for run.py (default: {provider}/{basename(model)})",
    )
    bench.add_argument(
        "--provider", default="vllm",
        help="Provider key for opencode config injection (default: vllm)",
    )

    # -- Output & Installation -------------------------------------------
    output = parser.add_argument_group("Output & Installation")
    output.add_argument(
        "--output-dir", required=True,
        help="Cluster path for results (auto-mounted to /nemo_run/code/results)",
    )
    output.add_argument(
        "--opencode-install-cmd", default=DEFAULT_INSTALL_CMD,
        help="Command to install Node.js + opencode CLI inside the container",
    )
    output.add_argument(
        "--skip-opencode-install", action="store_true",
        help="Skip opencode CLI installation (assumes it is already available in the container)",
    )

    return parser


# ---------------------------------------------------------------------------
# Command construction
# ---------------------------------------------------------------------------

def build_config_inject_cmd(provider, model_id, server_url):
    """Return a shell snippet that injects a full provider config into every opencode.json.

    opencode-ai requires custom providers to declare ``npm`` (the AI SDK adapter),
    ``models`` (with at least the model being used), and ``api``/``options`` so that
    the CLI can resolve ``provider/model`` at runtime.  The previous implementation
    only set ``options.baseURL``, which caused ``ProviderModelNotFoundError`` because
    no models were registered under the provider.

    Uses ``python3 -c '...'`` instead of a heredoc because run_cmd's get_cmd()
    flattens the command into a single shell string, which breaks heredoc
    delimiter detection.
    """
    return (
        f"python3 -c '"
        f'import json, pathlib\n'
        f'provider_cfg = {{\n'
        f'    "npm": "@ai-sdk/openai-compatible",\n'
        f'    "name": "{provider}",\n'
        f'    "api": "{server_url}",\n'
        f'    "env": [],\n'
        f'    "options": {{"baseURL": "{server_url}", "apiKey": "EMPTY"}},\n'
        f'    "models": {{"{model_id}": {{"name": "{model_id}", "id": "{model_id}"}}}}\n'
        f'}}\n'
        f'for p in pathlib.Path("projects").rglob("opencode.json"):\n'
        f'    cfg = json.loads(p.read_text())\n'
        f'    cfg["disabled_providers"] = ["opencode"]\n'
        f'    cfg.setdefault("provider", {{}})["{provider}"] = provider_cfg\n'
        f"    p.write_text(json.dumps(cfg, indent=2))'"
    )


def build_benchmark_command(opencode_model, provider, server_url, timeout,
                            benchmark_ids, benchmark_categories):
    """Build the in-container shell command that runs the benchmark."""
    parts = []

    # Point RESULTS to the mounted /results directory
    parts.append("export OPENCODE_BENCH_RESULTS=/results")

    # Extract model ID (part after provider/) for config registration
    model_id = opencode_model.split("/", 1)[1] if "/" in opencode_model else opencode_model

    # Inject full provider config (npm adapter, model registration, baseURL) into project configs
    parts.append(build_config_inject_cmd(provider, model_id, server_url))

    # run.py  (no --proxy)
    run_args = [
        "cd /nemo_run/code/ && python run.py",
        f"--model {opencode_model}",
        f"--timeout {timeout}",
    ]
    if benchmark_ids:
        for bid in benchmark_ids:
            run_args.append(f"--id {bid}")
    if benchmark_categories:
        for cat in benchmark_categories:
            run_args.append(f"--category {cat}")
    parts.append(" ".join(run_args))

    # eval.py  (no proxy-related args)
    eval_args = [
        "cd /nemo_run/code/ && python eval.py",
        f"--model {opencode_model}",
        "--format json",
    ]
    if benchmark_ids:
        for bid in benchmark_ids:
            eval_args.append(f"--id {bid}")
    if benchmark_categories:
        for cat in benchmark_categories:
            eval_args.append(f"--category {cat}")
    parts.append(" ".join(eval_args))

    return " && ".join(parts)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = build_parser()
    args = parser.parse_args()

    # -- Validate server configuration -----------------------------------
    if not args.server_gpus and not args.server_address:
        parser.error("Either --server-gpus or --server-address is required")

    # -- Derive opencode model name --------------------------------------
    if args.opencode_model is None:
        basename = os.path.basename(args.model.rstrip("/"))
        opencode_model = f"{args.provider}/{basename}"
    else:
        opencode_model = args.opencode_model

    # model_id is the part after the provider prefix (e.g. "final_hf_model"
    # from "vllm/final_hf_model").  It must match both the opencode config
    # model registration and the vLLM --served-model-name.
    model_id = opencode_model.split("/", 1)[1] if "/" in opencode_model else opencode_model

    # -- Determine vLLM server URL ---------------------------------------
    if args.server_address:
        server_url = f"http://{args.server_address}/v1"
    else:
        server_url = f"http://localhost:{DEFAULT_SERVER_PORT}/v1"

    # -- Mount handling --------------------------------------------------
    # Append expname to output_dir (e.g. /lustre/.../results/my-exp)
    # and mount that as /results inside the container.  The benchmark
    # command sets OPENCODE_BENCH_RESULTS=/results so that common.py
    # writes directly to the mounted cluster storage.
    results_dir = os.path.join(args.output_dir.rstrip("/"), args.expname)
    log_dir = args.log_dir if args.log_dir else os.path.join(results_dir, "logs")

    # Create the results and log directories on the cluster before
    # submitting so the mount sources exist when Slurm starts the container.
    if not args.dry_run:
        cluster_config = get_cluster_config(args.cluster, args.config_dir)
        create_remote_directory([results_dir, log_dir], cluster_config)

    output_mount = f"{results_dir}:/results"
    if args.mount_paths:
        mount_paths = f"{args.mount_paths},{output_mount}"
    else:
        mount_paths = output_mount

    # Resolve log_dir to its container path (e.g. /results/logs) so that
    # run_cmd writes Slurm logs to the mounted volume.
    cluster_cfg = get_cluster_config(args.cluster, args.config_dir)
    resolve_mount_paths(cluster_cfg, mount_paths)
    mounted_log_dir = get_mounted_path(cluster_cfg, log_dir)

    # -- Build in-container command --------------------------------------
    bench_cmd = build_benchmark_command(
        opencode_model=opencode_model,
        provider=args.provider,
        server_url=server_url,
        timeout=args.timeout,
        benchmark_ids=args.benchmark_id,
        benchmark_categories=args.benchmark_category,
    )

    # -- Print summary ---------------------------------------------------
    print("=" * 72)
    print("opencode-bench cluster launcher")
    print("=" * 72)
    print(f"  Cluster:        {args.cluster}")
    print(f"  Experiment:     {args.expname}")
    print(f"  Model (HF):     {args.model}")
    print(f"  Model (OC):     {opencode_model}")
    print(f"  Model ID:       {model_id}")
    print(f"  Server URL:     {server_url}")
    if args.server_gpus:
        print(f"  Server GPUs:    {args.server_gpus} (x{args.server_nodes} node(s))")
    elif args.server_address:
        print(f"  Server addr:    {args.server_address} (external)")
    print(f"  Output dir:     {args.output_dir}")
    print(f"  Results dir:    {results_dir}")
    print(f"  Log dir:        {log_dir}")
    print(f"  Mount paths:    {mount_paths}")
    print(f"  Timeout:        {args.timeout}s per sample")
    if args.benchmark_id:
        print(f"  Sample IDs:     {args.benchmark_id}")
    if args.benchmark_category:
        print(f"  Categories:     {args.benchmark_category}")
    if not args.skip_opencode_install:
        print(f"  Install cmd:    {args.opencode_install_cmd}")
    if args.dry_run:
        print(f"  ** DRY RUN **")
    print("=" * 72)
    print(f"\nIn-container command:\n{bench_cmd}\n")

    # -- Build run_cmd kwargs --------------------------------------------
    run_cmd_kwargs = {
        "cluster": args.cluster,
        "command": bench_cmd,
        "container": args.container,
        "expname": args.expname,
        "num_nodes": args.num_nodes,
        "dry_run": args.dry_run,
        "dependent_jobs": args.dependent_jobs,
        "reuse_code": args.reuse_code,
        "mount_paths": mount_paths,
        "log_dir": mounted_log_dir,
    }

    # Server sidecar (only when hosting the model ourselves)
    if args.server_gpus:
        # NeMo-Skills' serve_vllm.py sets --served-model-name to the full
        # filesystem path by default.  Override it with model_id so vLLM
        # serves the model under the short name that opencode expects.
        server_args = args.server_args or ""
        if "--served-model-name" not in server_args:
            server_args = f'{server_args} --served-model-name="{model_id}"'.strip()

        run_cmd_kwargs.update(
            model=args.model,
            server_gpus=args.server_gpus,
            server_nodes=args.server_nodes,
            server_type=args.server_type,
            server_args=server_args,
        )
    elif args.server_address:
        run_cmd_kwargs.update(
            model=args.model,
            server_address=args.server_address,
        )

    # Installation command (Node.js + opencode)
    if not args.skip_opencode_install:
        run_cmd_kwargs["installation_command"] = args.opencode_install_cmd

    # Optional kwargs (only pass when set to avoid overriding run_cmd defaults)
    for attr in ("config_dir", "num_gpus", "partition", "qos", "time_min"):
        val = getattr(args, attr.replace("-", "_"), None)
        if val is not None:
            run_cmd_kwargs[attr] = val

    # -- Submit ----------------------------------------------------------
    try:
        ctx = wrap_arguments("")
        result = run_cmd(ctx=ctx, **run_cmd_kwargs)

        if args.dry_run:
            print("\nDry run completed successfully.")
        else:
            print(f"\nJob submitted successfully: {result}")

    except Exception as e:
        print(f"\nError submitting job: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
