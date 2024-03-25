from flytekit import ImageSpec, task, workflow

image = ImageSpec(
    # builder="fast-builder",
    builder="envd",
    packages=["numpy"],
    env={"a": "b", "c": "d", "j": "k"},
    registry="ghcr.io/thomasjpfan",
)


@task(container_image=image)
def my_task() -> int:
    import numpy as np

    X = np.asarray([1, 2, 3])
    return int(X[1])


@workflow
def wf() -> int:
    return my_task()
