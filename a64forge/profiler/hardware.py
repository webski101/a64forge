from __future__ import annotations

import os
import platform
import re
import shutil
import socket
import subprocess
from pathlib import Path

import psutil

from a64forge.config import env_flag
from a64forge.schemas import Detection, HardwareInfo

ARM64_NAMES = {"aarch64", "arm64", "armv8l", "armv9l"}


def _command(name: str, override: str | None = None) -> str | None:
    if override:
        candidate = Path(override)
        if candidate.exists():
            return str(candidate)
    for executable in (name, name.replace("-", " ")):
        found = shutil.which(executable)
        if found:
            return found
    return None


def _cpu_model() -> str:
    if platform.system() == "Linux":
        cpuinfo = Path("/proc/cpuinfo")
        if cpuinfo.exists():
            text = cpuinfo.read_text(encoding="utf-8", errors="ignore")
            for key in ("model name", "Model", "Hardware", "Processor"):
                match = re.search(rf"^{re.escape(key)}\s*:\s*(.+)$", text, re.MULTILINE)
                if match:
                    return match.group(1).strip()
    return platform.processor() or os.getenv("PROCESSOR_IDENTIFIER", "unknown")


def parse_arm_features(text: str) -> dict[str, Detection]:
    normalized = text.lower()

    def status(*needles: str) -> Detection:
        for needle in needles:
            explicit = re.search(rf"\b{re.escape(needle.lower())}\s*=\s*([01])", normalized)
            if explicit:
                return Detection.DETECTED if explicit.group(1) == "1" else Detection.UNAVAILABLE
        tokens = set(re.findall(r"[a-z0-9_]+", normalized))
        return Detection.DETECTED if any(needle.lower() in tokens for needle in needles) else Detection.UNKNOWN

    return {
        "neon": status("neon", "asimd"),
        "sve": status("sve"),
        "sve2": status("sve2"),
        "arm_fma": status("arm_fma", "fma"),
        "matmul_int8": status("matmul_int8", "i8mm"),
    }


def _feature_evidence() -> str:
    evidence: list[str] = []
    for path in (Path("/proc/cpuinfo"), Path("/sys/devices/system/cpu/cpu0/regs/identification/midr_el1")):
        if path.exists():
            evidence.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(evidence)


def _llama_evidence(executable: str | None) -> tuple[str | None, str | None]:
    if not executable:
        return None, None
    try:
        result = subprocess.run(
            [executable, "--version"], capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None, None
    raw = "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part)
    first_line = raw.splitlines()[0] if raw else None
    return first_line, raw or None


def detect_hardware() -> HardwareInfo:
    architecture = platform.machine().lower() or "unknown"
    arm64 = architecture in ARM64_NAMES
    dev_mode = env_flag("A64FORGE_DEV_MODE", default=not arm64)
    llama_server = _command("llama-server", os.getenv("A64FORGE_LLAMA_SERVER")) or _command("llama")
    llama_bench = _command("llama-bench", os.getenv("A64FORGE_LLAMA_BENCH"))
    llama_cli = _command("llama-cli") or _command("llama")
    version, llama_raw = _llama_evidence(llama_cli)
    features = parse_arm_features("\n".join(filter(None, [_feature_evidence(), llama_raw])))
    memory = psutil.virtual_memory()
    disk = shutil.disk_usage(Path.cwd())
    return HardwareInfo(
        architecture=architecture,
        cpu_model=_cpu_model(),
        logical_cores=psutil.cpu_count(logical=True) or 1,
        physical_cores=psutil.cpu_count(logical=False),
        memory_gb=round(memory.total / (1024**3), 2),
        available_memory_gb=round(memory.available / (1024**3), 2),
        os=f"{platform.system()} {platform.release()}",
        hostname=socket.gethostname(),
        arm64=arm64,
        **features,
        llama_cpp=llama_cli is not None,
        llama_server=llama_server is not None,
        llama_bench=llama_bench is not None,
        performix=_command("performix") is not None,
        llama_version=version,
        llama_system_info=llama_raw,
        disk_free_gb=round(disk.free / (1024**3), 2),
        dev_mode=dev_mode,
    )

