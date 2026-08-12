from a64forge.profiler.hardware import parse_arm_features
from a64forge.schemas import Detection


def test_parses_llama_arm_evidence() -> None:
    parsed = parse_arm_features("NEON = 1 | ARM_FMA = 1 | SVE = 1 | MATMUL_INT8 = 0")
    assert parsed["neon"] == Detection.DETECTED
    assert parsed["sve"] == Detection.DETECTED
    assert parsed["arm_fma"] == Detection.DETECTED
    assert parsed["matmul_int8"] == Detection.UNAVAILABLE
    assert parsed["sve2"] == Detection.UNKNOWN


def test_does_not_invent_features() -> None:
    assert parse_arm_features("generic cpu")["neon"] == Detection.UNKNOWN

