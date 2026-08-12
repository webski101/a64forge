# Free native Arm64 benchmark with GitHub Actions

This workflow uses GitHub's standard native Arm64 runner. Standard runners are
free for public repositories. It does not create an AWS instance, require an
AWS plan upgrade, or leave a server running after the job finishes.

## What it measures

- Native `aarch64` host evidence from the ephemeral runner.
- A pinned `llama.cpp` release compiled with `-mcpu=native`.
- Qwen3 0.6B Q4/Q8 and Qwen3 1.7B Q4 configurations.
- Five deterministic ResearchOps stages with quality gates.
- Latency, throughput, process memory/CPU, model and dataset hashes.

The dedicated `configs/github-arm64.yaml` profile is bounded for the runner's
memory, disk, and six-hour job limit. It does not replace `configs/default.yaml`.

## Run it

1. Push this repository to a **public** GitHub repository.
2. Open the repository's **Actions** tab.
3. Select **Native Arm64 benchmark**.
4. Click **Run workflow**, choose a target, and confirm.
5. Wait for the job to finish.
6. Open the completed run and download `a64forge-arm64-evidence-<run-id>`.

The workflow is manual-only and has a five-hour hard timeout. It validates that
the report label is `VERIFIED ARM64 RUN` before completing successfully. Models
are not included in the uploaded artifact.

## Important limitations

- GitHub runners are ephemeral and may vary between runs.
- Use one successful run for a single before/after story; do not combine metrics
  from different hosts or run IDs.
- The runner cannot host the dashboard after the workflow ends. Download the
  evidence artifact and load it locally instead.
- Public-preview runner availability can cause queue delays.
