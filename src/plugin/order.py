"""kill_order: the order a low-memory killer closes apps in, and the apps it never closes."""

from __future__ import annotations

from pathlib import Path

from contract import KillOrderInput, KillOrderOutput
from plugin.system import CLOSE_FIRST, check_apps, is_protected


def kill_order(request: KillOrderInput, workspace: Path) -> KillOrderOutput:
    check_apps(request.apps)
    closable = [app for app in request.apps if not is_protected(app)]
    closable.sort(key=lambda app: (CLOSE_FIRST.index(app.app_class), -app.memory_mb, -app.idle_s, app.name))
    return KillOrderOutput(
        order=[app.name for app in closable],
        protected=[app.name for app in request.apps if is_protected(app)],
    )
