# Verified Arm64 result

## Provenance

- GitHub Actions run: [31646296185](https://github.com/webski101/a64forge/actions/runs/31646296185)
- Benchmark run: `run-1488b44fa409`
- Source commit: `b414b9e8d52ea72dc909b92d87ba8a0efbd9c2d4`
- Artifact SHA-256: `cd6c525b236697308d0ad42fab026385ad614e75b8583defca24d532ebba9d3c`
- Host architecture: native `aarch64`
- Host resources: 4 physical cores, 15.57 GB RAM
- Runtime evidence: llama-server and llama-bench available; NEON, SVE, SVE2, and MATMUL_INT8 detected
- Measurements: 20 records across five ResearchOps stages
- Quality constraint: minimum 0.80, with the configured per-stage maximum-drop rule

## Baseline and result

The submission comparison uses one measured Qwen3-4B Q4 configuration for every stage as the conventional oversized-workflow baseline:

`large:Q4_K_M:t1:b64:c512`

The baseline and selected routes were measured in the same run, on the same host, against the same per-stage datasets. The baseline override changes only which already-measured records are used for comparison; it does not alter measurements or rerun inference.

| Workflow-average metric | All-4B baseline | Stage-aware routing | Change |
| --- | ---: | ---: | ---: |
| Median stage latency | 12,248.46 ms | 3,947.69 ms | 67.8% lower |
| Peak RSS | 4,897.91 MB | 2,796.18 MB | 42.9% lower |
| Requests per minute | 5.93 | 20.43 | 244.5% higher |
| Deterministic quality | 0.875 | 0.933 | 6.7% higher |

## Compiled routing

| Stage | Model | Quantization | Threads | Batch | Context | Quality |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| classify | Qwen3-4B | Q4_K_M | 1 | 64 | 512 | 1.000 |
| extract | Qwen3-1.7B | Q4_K_M | 4 | 128 | 1024 | 0.833 |
| tool_select | Qwen3-4B | Q4_K_M | 1 | 128 | 512 | 1.000 |
| reason | Qwen3-0.6B | Q4_0 | 1 | 64 | 2048 | 0.833 |
| summarize | Qwen3-0.6B | Q4_0 | 1 | 128 | 2048 | 1.000 |

Classification and tool selection retain the 4B model because smaller candidates did not satisfy their quality requirements. A64Forge selects smaller models only for stages where the measured quality gate permits it.

## Reproduce the analysis

```bash
a64forge import-evidence a64forge-arm64-evidence-31646296185.zip
a64forge optimize --run-id run-1488b44fa409 \
  --baseline large:Q4_K_M:t1:b64:c512 --target balanced
a64forge compile
a64forge report
a64forge serve
```
