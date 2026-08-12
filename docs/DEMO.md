# Three-minute demo

## 0:00–0:15 — Problem

“AI agents commonly run one oversized model with generic settings for every stage.”

## 0:15–0:30 — A64Forge

“A64Forge recompiles an agent for the Arm CPU beneath it.” Show the workflow graph and stage quality gates.

## 0:30–0:45 — Prove Arm

Open **Arm System**. Show architecture, real CPU, cores, llama.cpp build evidence, NEON/SVE/MATMUL_INT8 detection, and the `VERIFIED ARM64 RUN` label.

## 0:45–1:20 — Optimize

Click **Optimize for Arm64**. Show the live compiler log loading candidates, changing threads/batches/context, evaluating quality, and storing evidence.

## 1:20–1:45 — Workflow transformation

Show the baseline topology becoming measured stage-specific routing.

## 1:45–2:20 — Results

Show the actual median/p95 latency, throughput, peak RSS, and quality. Do not record this segment until real values exist.

## 2:20–2:40 — Pareto frontier

Explain why the winner passes the quality floor and why dominated candidates were discarded.

## 2:40–3:00 — Developer artifact

```bash
a64forge autopilot
a64forge compile
a64forge serve
```

End: **A64Forge — compile once. Run Arm-native.**

