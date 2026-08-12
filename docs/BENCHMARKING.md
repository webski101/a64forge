# Benchmark methodology

A64Forge runs a bounded, deterministic candidate matrix per workflow stage. It includes the configured baseline, samples the larger model/runtime space, performs configured warm-ups, executes multiple measured passes over the same JSONL dataset, and stores the median and interpolated p95. Quality is evaluated from references without an external paid judge.

Fair comparisons require the same host, workflow dataset hash, generation limits, repetitions, and runtime build. Every record stores those inputs plus the Git commit and model SHA-256. Failed candidates remain visible with an error. Missing measurements remain `null` and render as “Not measured yet.”

The balanced score uses min-max normalization on the eligible Pareto frontier:

```text
score = 0.35 × latency + 0.20 × memory + 0.20 × throughput + 0.25 × quality
```

Latency and memory are inverted after normalization; throughput and quality are not. Other presets change only the published weights in `a64forge/optimizer/scorer.py`.

