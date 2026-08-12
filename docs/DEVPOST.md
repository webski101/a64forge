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

Separating responsive developer UX from scientific evidence, and keeping optional performance tools from becoming hard dependencies.

## Accomplishments we're proud of

The optimization system—not the sample agent—is the product. It emits reusable routing and evidence artifacts.

## What we learned

{{ARM64_LEARNING}}

## What's next for A64Forge

Additional workflow adapters, remote Arm workers, vLLM/ExecuTorch runtimes, and CI regression gates.

Final measured results: {{REAL_LATENCY_IMPROVEMENT}}, {{REAL_MEMORY_REDUCTION}}, {{REAL_THROUGHPUT_IMPROVEMENT}}, {{REAL_QUALITY_CHANGE}}.

