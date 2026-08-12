# Run on a real Arm64 host

## Implemented and tested

- Configuration, workflow adapters, deterministic quality metrics, Pareto optimization, routing compiler, API, report generator, and x86 development-mode safeguards.
- llama-server runner with warm-ups, repeated measurements, wall-clock and llama timing capture, model/dataset hashing, RSS/CPU sampling, timeouts, and memory preflight.

## Implemented but requires Arm64 validation

- Native llama.cpp build and detection of NEON, SVE, SVE2, FMA, and MATMUL_INT8.
- Final throughput, latency, TTFT (when exposed), memory, and quality records.
- Optional Performix capture template for the locally installed release.

## Commands

```bash
git clone <repository-url> a64forge
cd a64forge
./scripts/setup_arm64.sh
source .venv/bin/activate
export A64FORGE_DEV_MODE=false
export A64FORGE_LLAMA_SERVER="$PWD/.a64forge/llama.cpp/build/bin/llama-server"
python scripts/download_models.py
a64forge doctor
a64forge analyze examples/research_agent
a64forge benchmark --max-memory 12 --max-runtime 3600 --max-candidates 20
a64forge optimize --target balanced
a64forge compile
a64forge report
a64forge serve --host 0.0.0.0 --port 8640
```

Do not submit results unless every compared record says `VERIFIED ARM64 RUN` and the host evidence names the actual CPU.

