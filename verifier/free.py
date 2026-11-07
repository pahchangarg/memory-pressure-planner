"""The free-memory task: close apps to get under the target for the least total reopen time."""

from .checks import cheapest, close_problem, first_problem, machine_problem, result, used


def input_problem(value):
    return first_problem(
        machine_problem(value.total_mb, value.os_mb, value.apps),
        None if 0 <= value.target_mb <= value.total_mb else "target_mb must be 0 to total_mb",
    )


def verify_task(arguments, output, reference, workspace):
    problem = input_problem(arguments)
    if problem:
        return result(False, f"the request is not valid: {problem}")
    need = used(arguments.os_mb, arguments.apps) - arguments.target_mb
    best = cheapest(arguments.apps, need)
    problem = close_problem(arguments.apps, output.close)
    if problem:
        return result(False, problem)
    gone = [app for app in arguments.apps if app.name in output.close]
    cost = sum(app.reopen_s for app in gone)
    if output.reopen_s != cost:
        return result(False, f"those apps take {cost} s to reopen, not {output.reopen_s}")
    if best is None:
        if output.possible or output.close:
            return result(False, f"even closing every app that is not protected frees too little: need {need} MB")
        return result(True, "the target cannot be reached, and the output says so")
    if not output.possible:
        return result(False, f"the target can be reached for {best} s of reopening", expected=best)
    freed = sum(app.memory_mb for app in gone)
    if freed < need:
        return result(False, f"closing them frees {freed} MB, but {need} MB must go", expected=best)
    if cost > best:
        return result(False, f"they cost {cost} s to reopen, but {best} s is enough", expected=best)
    return result(True, f"frees {freed} MB of the {max(need, 0)} MB needed for {cost} s of reopening", reopen_s=cost)
