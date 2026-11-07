"""memory_pressure: how much RAM is used, and how hard the machine is pressed."""

from __future__ import annotations

from pathlib import Path

from contract import PressureInput, PressureOutput
from plugin.system import check_machine, level, used


def memory_pressure(request: PressureInput, workspace: Path) -> PressureOutput:
    check_machine(request.total_mb, request.os_mb, request.apps)
    used_mb = used(request.os_mb, request.apps)
    return PressureOutput(used_mb=used_mb, free_mb=request.total_mb - used_mb, level=level(used_mb, request.total_mb))
