from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class LlamaCppRuntime:
    def __init__(self, server: str = "llama-server", bench: str = "llama-bench") -> None:
        self.server = shutil.which(server)
        self.bench = shutil.which(bench)

    def require_server(self) -> Path:
        if not self.server:
            raise RuntimeError(
                "A64Forge could not find llama-server. Run scripts/build_llama_cpp.sh "
                "or configure A64FORGE_LLAMA_SERVER."
            )
        return Path(self.server)

    def version(self) -> str | None:
        if not self.server:
            return None
        result = subprocess.run(
            [self.server, "--version"], capture_output=True, text=True, check=False, timeout=10
        )
        return (result.stdout or result.stderr).strip() or None

