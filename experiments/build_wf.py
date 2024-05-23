from flytekit import ImageSpec, task, workflow

image = ImageSpec(
    builder="fast-builder",
    # builder="envd",
    # packages=["numpy"],
    conda_packages=["numpy"],
    # registry="localhost:30000",
    registry="ghcr.io/thomasjpfan",
    env={"ABC": "CDE"},
)


@task(container_image=image)
def my_task() -> int:
    import numpy as np

    X = np.asarray([1, 2, 3])
    return int(X[1])


@workflow
def wf() -> int:
    return my_task()
