# Official research notes

Research checked on 9 August 2026. Arm sources are authoritative for Arm-specific decisions; llama.cpp and GGUF sources are authoritative for runtime behavior and file metadata.

## Challenge and judging

- [Arm Create](https://developer.arm.com/arm-create) confirms the 2026 AI Optimization Challenge and its emphasis on optimized AI across physical, cloud, and mobile Arm platforms. This fixed A64Forge on the Cloud AI track rather than a generic local-AI demo.
- [Challenge overview and judging](https://arm-ai-optimization-challenge.devpost.com/) assigns 40 points to technical implementation, 15 to developer experience, 20 to potential impact, and 25 to WOW factor. It explicitly asks for measurable model size, quality, speed, server speed, developer-experience, and Arm-specific improvements. A64Forge therefore stores reproducible evidence and emits reusable deployment artifacts.
- [Cloud AI track details](https://arm-ai-optimization-challenge.devpost.com/details/trackdetails) explicitly includes Arm64 cloud/server inference, quantization, CPU-optimized llama.cpp, and agentic workloads. This directly validates the stage-aware CPU-inference compiler architecture.
- [Official rules](https://arm-ai-optimization-challenge.devpost.com/rules) require runnable source, a public repository, an MIT or Apache-2.0 license, setup instructions, and consistency between the project and its demo. A64Forge uses Apache-2.0 and refuses to label development fixtures as verified measurements.
- [Strengthen Your Optimization Story](https://arm-ai-optimization-challenge.devpost.com/updates/45456-arm-ai-optimization-challenge-strengthen-your-optimization-story) says that merely running on Arm is insufficient: submissions must show what changed, how it improved the system, and the evidence. This drove the before/after comparison, Pareto reasoning, decision explanations, and report manifest.

## Arm and llama.cpp

- [Arm llama.cpp + KleidiAI learning path](https://learn.arm.com/learning-paths/servers-and-cloud-computing/llama-cpu/llama-chatbot/) builds with CMake and `-mcpu=native`; current llama.cpp detects Arm features and includes contributed kernels. It identifies runtime evidence such as `NEON`, `ARM_FMA`, `MATMUL_INT8`, and `SVE`. The setup script follows this documented build and the doctor parses evidence instead of inventing a KleidiAI flag.
- [Arm AI-agent learning path](https://learn.arm.com/learning-paths/servers-and-cloud-computing/ai-agent-on-cpu/) demonstrates local, function-calling agents on Arm using llama.cpp. This supports the ResearchOps workflow while A64Forge keeps its own adapter boundary rather than depending on one agent framework.
- [Arm OpenAI-compatible llama-server guide](https://learn.arm.com/learning-paths/servers-and-cloud-computing/llama-cpu/llama-server/) shows `/v1/chat/completions` and response `timings` fields for prompt and generation throughput. The benchmark runner uses those real response fields and wall-clock timing; no timing is synthesized.
- [llama.cpp](https://github.com/ggml-org/llama.cpp) documents CPU inference, GGUF, quantization, and current `llama serve` / `llama-server` usage. A64Forge detects both current and legacy executable names.
- [llama-server documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md) documents OpenAI-compatible routes, continuous batching, parallel decoding, server metrics, and current runtime flags. A64Forge limits itself to documented common flags and captures `--version` evidence.
- [GGUF specification](https://github.com/ggml-org/ggml/blob/master/docs/gguf.md) defines architecture, quantization, license, provenance, and context metadata. A64Forge hashes local model bytes and treats registry labels as configuration, not proof of a file's contents.

## Performix

- [Arm Performix](https://developer.arm.com/servers-and-cloud-computing/arm-performix) describes a free profiling toolkit for Arm Neoverse with function-level, CPU, memory, and automation-ready output. The integration is an optional command adapter; if the CLI is absent, core benchmarking remains operational and the report says `unavailable`.

## Default model registry

Defaults are references, not redistributed weights. All are ungated Apache-2.0 GGUF repositories and must still be downloaded by the user:

- [ggml-org/Qwen3-0.6B-GGUF](https://huggingface.co/ggml-org/Qwen3-0.6B-GGUF): Q4_0 (about 429 MB) and Q8_0 (about 805 MB). Small classification/tool-routing candidate.
- [ggml-org/Qwen3-1.7B-GGUF](https://huggingface.co/ggml-org/Qwen3-1.7B-GGUF): Q4_K_M (about 1.28 GB) and Q8_0 (about 2.17 GB). Mid-size extraction/summarization candidate.
- [Qwen/Qwen3-4B-GGUF](https://huggingface.co/Qwen/Qwen3-4B-GGUF): Q4_K_M (about 2.5 GB), Q5_K_M (about 2.89 GB), and Q8_0 (about 4.28 GB). Reasoning candidate.

Actual RAM includes the model, KV cache, runtime buffers, and process overhead; A64Forge checks free memory and does not equate disk size with peak RSS.

