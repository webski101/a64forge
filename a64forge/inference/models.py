from __future__ import annotations

from pathlib import Path

from a64forge.schemas import ModelSpec, ModelVariant


class ModelRegistry:
    def __init__(self, models: list[ModelSpec]) -> None:
        self.models = {model.id: model for model in models}

    def resolve(self, model_id: str, quantization: str) -> tuple[ModelSpec, ModelVariant, Path]:
        model = self.models.get(model_id)
        if model is None:
            raise KeyError(f"Unknown model: {model_id}")
        variant = next((item for item in model.variants if item.quantization == quantization), None)
        if variant is None:
            raise KeyError(f"{model_id} has no {quantization} variant")
        if variant.path is None or not variant.path.exists():
            raise FileNotFoundError(
                f"Model file not found for {model_id}/{quantization}: {variant.path or 'no path configured'}"
            )
        return model, variant, variant.path

