#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "A64Forge Arm setup requires Linux (Ubuntu 22.04/24.04 recommended)."
  exit 1
fi

arch="$(uname -m)"
if [[ "$arch" != "aarch64" && "$arch" != "arm64" ]]; then
  echo "WARNING:"
  echo "This machine is $arch."
  echo "Development mode is supported, but official A64Forge performance measurements must be executed on an Arm64 machine."
  exit 1
fi

sudo apt-get update
sudo apt-get install -y build-essential cmake git jq python3 python3-pip python3-venv
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
bash scripts/build_llama_cpp.sh
echo "export A64FORGE_LLAMA_SERVER=${LLAMA_CPP_DIR:-$PWD/.a64forge/llama.cpp}/build/bin/llama-server"
echo "export A64FORGE_LLAMA_BENCH=${LLAMA_CPP_DIR:-$PWD/.a64forge/llama.cpp}/build/bin/llama-bench"
echo "Run: source .venv/bin/activate && a64forge doctor"

