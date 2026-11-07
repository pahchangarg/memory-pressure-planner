"""close_apps: close some apps and report the memory, pressure and reopen time that follow."""

from __future__ import annotations

from pathlib import Path

from contract import CloseInput, CloseOutput
from plugin.system import check_close, check_machine, level, used


def close_apps(request: CloseInput, workspace: Path) -> CloseOutput:
    check_machine(request.total_mb, request.os_mb, request.apps)
    closing = check_close(request.apps, request.close)
    kept = [app for app in request.apps if app.name not in request.close]
    used_mb = used(request.os_mb, kept)
    return CloseOutput(
        freed_mb=sum(app.memory_mb for app in closing),
        used_mb=used_mb,
        free_mb=request.total_mb - used_mb,
        level=level(used_mb, request.total_mb),
        reopen_s=sum(app.reopen_s for app in closing),
        kept=[app.name for app in kept],
    )
