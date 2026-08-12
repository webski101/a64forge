from a64forge.benchmark.matrix import (
    generate_coarse_matrix,
    generate_fine_matrix,
    select_diverse_coarse,
)
from a64forge.config import load_project_config
from a64forge.schemas import BenchmarkCandidate


def test_search_matrices_are_bounded_and_fine_search_excludes_seed() -> None:
    config = load_project_config()
    coarse = generate_coarse_matrix(config)
    assert len(coarse) <= config.search.max_candidates

    variant = config.models[0].variants[0]
    seed = BenchmarkCandidate(
        model_id=config.models[0].id,
        model_name=config.models[0].name,
        model_repo=config.models[0].repo,
        model_path=variant.path,
        quantization=variant.quantization,
        threads=config.search.threads[1],
        batch_size=config.search.batch_sizes[1],
        context_size=config.search.context_sizes[1],
    )
    fine = generate_fine_matrix(config, [seed], remaining=4)
    assert 0 < len(fine) <= 4
    assert seed.key not in {item.key for item in fine}
    assert all(item.model_id == seed.model_id for item in fine)


def test_coarse_selection_prefers_model_quantization_diversity() -> None:
    config = load_project_config()
    matrix = generate_coarse_matrix(config)
    baseline_model = next(item for item in config.models if item.id == config.baseline_model)
    baseline_variant = next(
        item
        for item in baseline_model.variants
        if item.quantization == config.baseline_quantization
    )
    baseline = BenchmarkCandidate(
        model_id=baseline_model.id,
        model_name=baseline_model.name,
        model_repo=baseline_model.repo,
        model_path=baseline_variant.path,
        quantization=baseline_variant.quantization,
        threads=config.baseline_threads,
        batch_size=config.baseline_batch_size,
        context_size=config.baseline_context_size,
    )
    selected = select_diverse_coarse(matrix, baseline, limit=3)
    variants = {(item.model_id, item.quantization) for item in selected}
    assert selected[0].key == baseline.key
    assert len(selected) == 3
    assert len(variants) == 3
