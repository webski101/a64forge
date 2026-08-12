# Arm64 setup

Use Ubuntu 22.04 or 24.04 on a real `aarch64` server. The build script follows the current Arm learning path: CMake release build with `-mcpu=native`; it does not invent a KleidiAI switch. Current llama.cpp contains Arm-contributed kernels and prints the detected feature evidence.

```bash
./scripts/setup_arm64.sh
export A64FORGE_LLAMA_SERVER="$PWD/.a64forge/llama.cpp/build/bin/llama-server"
export A64FORGE_LLAMA_BENCH="$PWD/.a64forge/llama.cpp/build/bin/llama-bench"
a64forge doctor
```

Confirm `architecture: aarch64`, `arm64: true`, and development mode is false before collecting final evidence.

