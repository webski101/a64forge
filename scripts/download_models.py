from __future__ import annotations

import argparse
from pathlib import Path

from a64forge.config import load_project_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Download configured GGUF references")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--model", action="append", help="Model id; repeat to select multiple")
    parser.add_argument("--output", type=Path, default=Path("models"))
    args = parser.parse_args()
    try:
        from huggingface_hub import hf_hub_download
    except ImportError as exc:
        raise SystemExit("Install huggingface-hub: python -m pip install huggingface-hub") from exc
    config = load_project_config(args.config)
    args.output.mkdir(parents=True, exist_ok=True)
    selected = set(args.model or [model.id for model in config.models])
    for model in config.models:
        if model.id not in selected:
            continue
        for variant in model.variants:
            if not variant.filename:
                continue
            print(f"Downloading {model.repo}/{variant.filename}")
            hf_hub_download(
                repo_id=model.repo,
                filename=variant.filename,
                local_dir=args.output,
            )


if __name__ == "__main__":
    main()

