from flytekit import ImageSpec
from imagespec_fast_builder import FastImageBuilder


image = ImageSpec(
    name="check-flytekit",
    builder="fast-builder",
    packages=["torch==2.3.0"],
    platform="linux/amd64",
    env={"hello": "world"},
)

builder = FastImageBuilder()
builder._build_image(image, push=False)
