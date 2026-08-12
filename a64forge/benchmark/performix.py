from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class PerformixAdapter:
    """Optional adapter with an intentionally conservative command surface.

    Performix command syntax can vary by release. Users configure the capture
    template explicitly; A64Forge never guesses flags or reports a capture that
    did not finish successfully.
    """

    def __init__(self, command: str = "performix", template: list[str] | None = None) -> None:
        self.command = shutil.which(command)
        self.template = template

    @property
    def available(self) -> bool:
        return self.command is not None

    def wrap(self, target: list[str], output_dir: Path) -> list[str]:
        if not self.available or not self.template:
            return target
        output_dir.mkdir(parents=True, exist_ok=True)
        substitutions = {"{output}": str(output_dir)}
        args = [substitutions.get(item, item) for item in self.template]
        return [self.command or "performix", *args, "--", *target]

    def validate(self) -> str | None:
        if not self.available:
            return None
        result = subprocess.run(
            [self.command or "performix", "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        return (result.stdout or result.stderr).strip() or None

