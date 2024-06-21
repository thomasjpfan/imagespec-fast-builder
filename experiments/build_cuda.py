from flytekit import ImageSpec, Resources, task

image = ImageSpec(
    name="pytorch",
    packages=["torch==2.3.1"],
    builder="fast-builder",
    registry="ghcr.io/thomasjpfan",
    env={"ABC": "EFG", "abc": "xyz"},
)
# This is the image from the above image spec
# image = "ghcr.io/thomasjpfan/pytorch:fpKDvHgYK_C3ukST8iGGAQ"


@task(container_image=image, requests=Resources(gpu="1"))
def check_torch() -> bool:
    import torch

    return torch.cuda.is_available()
