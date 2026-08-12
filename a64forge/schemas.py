from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class Detection(StrEnum):
    DETECTED = "detected"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class RunLabel(StrEnum):
    VERIFIED_ARM64 = "VERIFIED ARM64 RUN"
    DEVELOPMENT = "DEMO DATA"
    UNVERIFIED = "UNVERIFIED RUN"


class OptimizationStatus(StrEnum):
    DEPLOYABLE = "DEPLOYABLE"
    NO_QUALIFYING_CANDIDATE = "NO QUALIFYING CANDIDATE"


class HardwareInfo(BaseModel):
    architecture: str
    cpu_model: str
    logical_cores: int
    physical_cores: int | None
    memory_gb: float
    available_memory_gb: float
    os: str
    hostname: str
    arm64: bool
    neon: Detection = Detection.UNKNOWN
    sve: Detection = Detection.UNKNOWN
    sve2: Detection = Detection.UNKNOWN
    arm_fma: Detection = Detection.UNKNOWN
    matmul_int8: Detection = Detection.UNKNOWN
    llama_cpp: bool = False
    llama_server: bool = False
    llama_bench: bool = False
    performix: bool = False
    llama_version: str | None = None
    llama_system_info: str | None = None
    disk_free_gb: float
    dev_mode: bool

    @property
    def verified_arm64(self) -> bool:
        return self.arm64 and not self.dev_mode


class ModelVariant(BaseModel):
    quantization: str
    filename: str | None = None
    size_bytes: int | None = None
    path: Path | None = None


class ModelSpec(BaseModel):
    id: str
    name: str
    repo: str
    parameters_billions: float = Field(gt=0)
    license: str
    gated: bool = False
    variants: list[ModelVariant]

    @field_validator("variants")
    @classmethod
    def unique_variants(cls, value: list[ModelVariant]) -> list[ModelVariant]:
        names = [item.quantization for item in value]
        if len(names) != len(set(names)):
            raise ValueError("model quantizations must be unique")
        return value


QualityMetric = Literal[
    "exact_match",
    "structured_accuracy",
    "tool_accuracy",
    "reference_coverage",
    "factual_coverage",
]


class WorkflowStage(BaseModel):
    id: str
    type: str
    prompt: str
    quality_metric: QualityMetric
    dataset: Path
    max_tokens: int = Field(default=128, ge=1, le=4096)
    temperature: float = Field(default=0, ge=0, le=2)


class WorkflowSpec(BaseModel):
    name: str
    description: str = ""
    minimum_quality: float = Field(default=0.9, ge=0, le=1)
    maximum_quality_drop: float = Field(default=0.02, ge=0, le=1)
    stages: list[WorkflowStage]

    @field_validator("stages")
    @classmethod
    def unique_stages(cls, value: list[WorkflowStage]) -> list[WorkflowStage]:
        ids = [item.id for item in value]
        if not value:
            raise ValueError("workflow requires at least one stage")
        if len(ids) != len(set(ids)):
            raise ValueError("workflow stage ids must be unique")
        return value


class SearchConfig(BaseModel):
    threads: list[int] = Field(default_factory=lambda: [1, 2, 4, 8])
    batch_sizes: list[int] = Field(default_factory=lambda: [128, 256, 512])
    context_sizes: list[int] = Field(default_factory=lambda: [1024, 2048, 4096])
    repetitions: int = Field(default=3, ge=1, le=20)
    warmups: int = Field(default=1, ge=0, le=5)
    max_candidates: int = Field(default=24, ge=1, le=500)
    max_runtime_seconds: int = Field(default=3600, ge=30)
    max_memory_gb: float | None = Field(default=None, gt=0)
    request_timeout_seconds: int = Field(default=180, ge=5)

    @field_validator("threads", "batch_sizes", "context_sizes")
    @classmethod
    def positive_unique(cls, value: list[int]) -> list[int]:
        if not value or any(item <= 0 for item in value):
            raise ValueError("search values must be positive and non-empty")
        return sorted(set(value))


class CloudConfig(BaseModel):
    hourly_cost_usd: float | None = Field(default=None, ge=0)


class ProjectConfig(BaseModel):
    version: str = "1"
    workflow: Path
    models: list[ModelSpec]
    search: SearchConfig = Field(default_factory=SearchConfig)
    cloud: CloudConfig = Field(default_factory=CloudConfig)
    baseline_model: str
    baseline_quantization: str
    baseline_threads: int = Field(gt=0)
    baseline_batch_size: int = Field(gt=0)
    baseline_context_size: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_baseline(self) -> ProjectConfig:
        model = next((item for item in self.models if item.id == self.baseline_model), None)
        if model is None:
            raise ValueError("baseline_model must reference a configured model")
        variants = {item.quantization for item in model.variants}
        if self.baseline_quantization not in variants:
            raise ValueError("baseline_quantization is not available for baseline_model")
        return self


class BenchmarkCandidate(BaseModel):
    model_id: str
    model_name: str
    model_repo: str
    model_path: Path | None
    quantization: str
    threads: int
    batch_size: int
    context_size: int

    @property
    def key(self) -> str:
        return (
            f"{self.model_id}:{self.quantization}:t{self.threads}:"
            f"b{self.batch_size}:c{self.context_size}"
        )


class BenchmarkRecord(BaseModel):
    run_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    git_commit: str
    hostname: str
    architecture: str
    cpu: str
    cores: int
    ram_gb: float
    stage_id: str
    model: str
    model_repo: str
    model_hash: str | None
    quantization: str
    threads: int
    batch_size: int
    context_size: int
    prompt_tokens: int | None = None
    generated_tokens: int | None = None
    latency_ms: float | None = None
    median_latency_ms: float | None = None
    p95_latency_ms: float | None = None
    ttft_ms: float | None = None
    prompt_tokens_per_second: float | None = None
    generation_tokens_per_second: float | None = None
    total_tokens_per_second: float | None = None
    requests_per_minute: float | None = None
    peak_memory_mb: float | None = None
    average_cpu_percent: float | None = None
    peak_cpu_percent: float | None = None
    model_size_bytes: int | None = None
    load_time_ms: float | None = None
    quality_score: float | None = Field(default=None, ge=0, le=1)
    measured_runs: int = 0
    warmup_runs: int = 0
    run_label: RunLabel
    verified_arm64: bool = False
    dataset_hash: str
    error: str | None = None
    raw_artifact: Path | None = None
    performix_artifact: Path | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def verification_is_consistent(self) -> BenchmarkRecord:
        if self.verified_arm64 and self.run_label != RunLabel.VERIFIED_ARM64:
            raise ValueError("verified records must carry the VERIFIED ARM64 RUN label")
        if self.run_label == RunLabel.DEVELOPMENT and self.verified_arm64:
            raise ValueError("development records can never be verified")
        return self


class StageSelection(BaseModel):
    stage_id: str
    target: str
    selected: BenchmarkRecord
    pareto_keys: list[str]
    explanation: list[str]
    score: float


class StageRejection(BaseModel):
    stage_id: str
    quality_floor: float = Field(ge=0, le=1)
    best_candidate: BenchmarkRecord | None = None
    reason: str


class OptimizationResult(BaseModel):
    optimization_id: str
    run_id: str
    target: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    workflow: str
    minimum_quality: float
    status: OptimizationStatus = OptimizationStatus.DEPLOYABLE
    selections: list[StageSelection]
    rejections: list[StageRejection] = Field(default_factory=list)
    baseline: list[BenchmarkRecord]
    run_label: RunLabel

    @property
    def deployable(self) -> bool:
        return self.status == OptimizationStatus.DEPLOYABLE and not self.rejections

    @model_validator(mode="after")
    def status_matches_rejections(self) -> OptimizationResult:
        if self.rejections and self.status != OptimizationStatus.NO_QUALIFYING_CANDIDATE:
            raise ValueError("optimization results with rejected stages cannot be deployable")
        if not self.rejections and self.status == OptimizationStatus.NO_QUALIFYING_CANDIDATE:
            raise ValueError("a non-deployable optimization result must identify rejected stages")
        return self


class ProgressEvent(BaseModel):
    event: str
    message: str
    stage_id: str | None = None
    candidate_key: str | None = None
    progress: float | None = Field(default=None, ge=0, le=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
