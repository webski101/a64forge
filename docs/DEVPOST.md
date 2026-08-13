# A64Forge Devpost draft

## Inspiration

Multi-stage agents often pay the cost of their largest model at every stage, including simple classification and routing.

## What it does

A64Forge measures candidate GGUF model and llama.cpp runtime configurations per workflow stage on the actual host, applies deterministic quality gates, calculates a Pareto frontier, and compiles the selected routing into a deployable manifest and evidence report.

## How we built it

Python, FastAPI, Typer, SQLite, React, TypeScript, llama.cpp, optional Arm Performix, and portable JSON/HTML artifacts.

## Why Arm64

Cloud AI on Arm offers high-core-count CPU infrastructure. The project exposes actual Arm feature evidence and uses current upstream llama.cpp kernels rather than treating architecture as a deployment label.

## Optimization strategy

Bounded coarse search, quality filtering, Pareto dominance, then a documented preset score over the frontier.

## Benchmark methodology

Same host, dataset hash, generation limits, warm-up count, and measured repetitions. Model files are SHA-256 hashed. Missing values are never fabricated.

## Challenges we ran into

Our first bounded run showed that a 1.7B baseline could not meet classification quality. We preserved the 0.80 quality floor, added a measured 4B candidate, and made “no qualifying candidate” a first-class non-deployable result instead of weakening the gate. We also separated captured Arm64 evidence from the machine viewing the dashboard so a Windows development host is never presented as the benchmark host.

## Accomplishments we're proud of

The optimization system—not the sample agent—is the product. A native `aarch64` run measured 20 configurations and compiled a five-stage routing that keeps Qwen3-4B only where quality requires it, uses Qwen3-1.7B for extraction, and Qwen3-0.6B for reasoning and summarization. It emits reusable routing, Docker, manifest, and evidence artifacts.

## What we learned

Workflow-aware optimization matters more than choosing one universally “fast” model. On the same Arm host, smaller models improved reasoning and summarization efficiency, while classification and tool selection still required the 4B model to protect quality. Arm feature evidence and model hashes made that tradeoff reproducible rather than anecdotal.

## What's next for A64Forge

Additional workflow adapters, remote Arm workers, vLLM/ExecuTorch runtimes, and CI regression gates.

Final verified result against the measured all-Qwen3-4B Q4 workflow baseline: **67.8% lower average stage latency**, **42.9% lower average peak RSS**, **244.5% higher average request throughput**, and **6.7% higher average deterministic quality**. All values come from run `run-1488b44fa409` on one native `aarch64` GitHub runner with the same per-stage datasets and generation constraints.
