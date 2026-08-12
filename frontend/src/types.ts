export type Detection = "detected" | "unavailable" | "unknown";

export interface Hardware {
  architecture: string;
  cpu_model: string;
  logical_cores: number;
  physical_cores: number | null;
  memory_gb: number;
  available_memory_gb: number;
  os: string;
  hostname: string;
  arm64: boolean;
  neon: Detection;
  sve: Detection;
  sve2: Detection;
  arm_fma: Detection;
  matmul_int8: Detection;
  llama_cpp: boolean;
  llama_server: boolean;
  llama_bench: boolean;
  performix: boolean;
  llama_version: string | null;
  disk_free_gb: number;
  dev_mode: boolean;
}

export interface ModelVariant {
  quantization: string;
  filename: string | null;
  size_bytes: number | null;
  path: string | null;
}

export interface ModelSpec {
  id: string;
  name: string;
  repo: string;
  parameters_billions: number;
  license: string;
  gated: boolean;
  variants: ModelVariant[];
}

export interface Stage {
  id: string;
  type: string;
  quality_metric: string;
  max_tokens: number;
}

export interface Workflow {
  name: string;
  description: string;
  minimum_quality: number;
  maximum_quality_drop: number;
  stages: Stage[];
}

export interface BenchmarkRecord {
  run_id: string;
  timestamp: string;
  stage_id: string;
  model: string;
  model_repo: string;
  quantization: string;
  threads: number;
  batch_size: number;
  context_size: number;
  median_latency_ms: number | null;
  p95_latency_ms: number | null;
  ttft_ms: number | null;
  requests_per_minute: number | null;
  peak_memory_mb: number | null;
  quality_score: number | null;
  run_label: "VERIFIED ARM64 RUN" | "DEMO DATA" | "UNVERIFIED RUN";
  verified_arm64: boolean;
  error: string | null;
}

export interface Selection {
  stage_id: string;
  target: string;
  selected: BenchmarkRecord;
  explanation: string[];
  score: number;
}

export interface StageRejection {
  stage_id: string;
  quality_floor: number;
  best_candidate: BenchmarkRecord | null;
  reason: string;
}

export interface Optimization {
  optimization_id: string;
  run_id: string;
  target: string;
  workflow: string;
  run_label: BenchmarkRecord["run_label"];
  status: "DEPLOYABLE" | "NO QUALIFYING CANDIDATE";
  selections: Selection[];
  rejections: StageRejection[];
  baseline: BenchmarkRecord[];
}

export interface ProgressEvent {
  event: string;
  message: string;
  stage_id: string | null;
  candidate_key: string | null;
  progress: number | null;
  timestamp: string;
}
