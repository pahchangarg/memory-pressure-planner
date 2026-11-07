"""kill_order and the kill-order task."""

from .checks import apps_problem, kill_order, protected, result


def verify_input(value):
    problem = apps_problem(value.apps)
    return result(problem is None, problem or "valid apps")


def verify_output(given, made, workspace):
    problem = apps_problem(given.apps)
    if problem:
        return result(False, f"the request is not valid: {problem}")
    keep = [app.name for app in given.apps if protected(app)]
    if made.protected != keep:
        return result(False, f"the protected apps are {keep}")
    order = kill_order(given.apps)
    if made.order != order:
        return result(False, f"the kill order is {order}")
    return result(True, f"{len(order)} apps in kill order, {len(keep)} protected")
