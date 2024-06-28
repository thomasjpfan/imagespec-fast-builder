from flytekit import ImageSpec
from imagespec_fast_builder import FastImageBuilder


image = ImageSpec(
    name="check-flytekit",
    builder="fast-builder",
    commands=["mkdir /hello", "touch /hello/world.txt"],
)

builder = FastImageBuilder()
builder._build_image(image, push=False)
