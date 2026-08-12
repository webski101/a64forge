from pathlib import Path

import pytest
from pydantic import ValidationError

from a64forge.schemas import ModelSpec, ModelVariant, ProjectConfig


def test_config_rejects_missing_baseline_variant() -> None:
    with pytest.raises(ValidationError):
        ProjectConfig(
            workflow=Path("workflow.yaml"),
            models=[ModelSpec(id="small", name="Small", repo="x/y", parameters_billions=1, license="Apache-2.0", variants=[ModelVariant(quantization="Q4")])],
            baseline_model="small",
            baseline_quantization="Q8",
            baseline_threads=4,
            baseline_batch_size=128,
            baseline_context_size=1024,
        )

