#!/usr/bin/env bash
set -euo pipefail

arch="$(uname -m)"
if [[ "$arch" != "aarch64" && "$arch" != "arm64" ]]; then
  echo "WARNING:"
  echo "This machine is $arch."
  echo "Development mode is supported, but official A64Forge measurements must run on Arm64."
  exit 1
fi

root="${LLAMA_CPP_DIR:-$PWD/.a64forge/llama.cpp}"
ref="${LLAMA_CPP_REF:-}"
if [[ ! -d "$root/.git" ]]; then
  if [[ -n "$ref" ]]; then
    git clone --depth 1 --branch "$ref" https://github.com/ggml-org/llama.cpp.git "$root"
  else
    git clone https://github.com/ggml-org/llama.cpp.git "$root"
  fi
elif [[ -n "$ref" ]]; then
  git -C "$root" fetch --depth 1 origin "$ref"
  git -C "$root" checkout --detach FETCH_HEAD
fi

echo "llama.cpp revision: $(git -C "$root" rev-parse HEAD)"

cmake -S "$root" -B "$root/build" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_FLAGS="-mcpu=native" \
  -DCMAKE_CXX_FLAGS="-mcpu=native"
cmake --build "$root/build" --config Release -j "$(nproc)" --target llama-server llama-bench llama-cli
"$root/build/bin/llama-server" --version
"$root/build/bin/llama-bench" --help >/dev/null
echo "llama.cpp built for $arch at $root/build/bin"
