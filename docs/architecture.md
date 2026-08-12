# Architecture

```mermaid
flowchart TD
  A[Existing AI workflow] --> B[Workflow profiler]
  B --> C[Coarse candidate generator]
  C --> D[Arm64 benchmark engine]
  D --> E[llama.cpp / llama-server]
  D -. optional .-> F[Arm Performix]
  E --> G[Quality gate]
  F --> G
  G --> H[Pareto optimizer]
  H --> I[Stage-aware compiler]
  I --> J[Optimized Arm64 deployment]
  D --> K[(SQLite + JSON evidence)]
  K --> L[Portable HTML report]
```

The benchmark engine never infers performance from parameter counts. It executes the configured runtime, records response and process metrics, evaluates stage-specific quality against deterministic fixtures, and stores the evidence. Only records produced on a detected `aarch64`/`arm64` host with development mode disabled receive `VERIFIED ARM64 RUN`.

