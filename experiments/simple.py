from flytekit import task, workflow


@task
def fn(i: int) -> int:
    if i < 0:
        return -1
    return i + 1


@workflow
def main(i: int) -> int:
    return fn(i=i)
