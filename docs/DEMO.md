# Three-minute demo

## 0:00–0:15 — Problem

“AI agents commonly run one oversized model with generic settings for every stage.”

## 0:15–0:30 — A64Forge

“A64Forge recompiles an agent for the Arm CPU beneath it.” Show the workflow graph and stage quality gates.

## 0:30–0:45 — Prove Arm

Open **Arm System**. Show `aarch64`, four cores, 15.57 GB RAM, NEON/SVE/SVE2/MATMUL_INT8 detection, and the `VERIFIED ARM64 RUN` label. Point out that the banner names imported run `run-1488b44fa409`; the viewing laptop is not being presented as the benchmark host.

## 0:45–1:20 — Optimize

Briefly show the completed GitHub Actions run and its downloadable evidence artifact, then return to **Optimization Lab**. Explain that 20 model/runtime configurations were measured and the 0.80 quality gate was never lowered.

## 1:20–1:45 — Workflow transformation

Show the measured all-4B Q4 baseline becoming stage-specific routing: 4B for classify/tool selection, 1.7B for extraction, and 0.6B for reasoning/summarization.

## 1:45–2:20 — Results

Show the verified workflow averages: 12,248.46 → 3,947.69 ms median stage latency; 4,897.91 → 2,796.18 MB peak RSS; 5.93 → 20.43 req/min; and 0.875 → 0.933 deterministic quality.

## 2:20–2:40 — Pareto frontier

Explain why the winner passes the quality floor and why dominated candidates were discarded.

## 2:40–3:00 — Developer artifact

```bash
a64forge import-evidence evidence.zip
a64forge optimize --baseline large:Q4_K_M:t1:b64:c512
a64forge compile
a64forge serve
```

End: **A64Forge — compile once. Run Arm-native.**
