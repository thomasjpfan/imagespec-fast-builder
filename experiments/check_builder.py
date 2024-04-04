from flytekit import ImageSpec
from imagespec_fast_builder import FastImageBuilder

image_spec = ImageSpec(
    name="flyte_playground",
    builder="fast-builder",
    packages=["numpy==1.26.4"],
    registry="localhost:30000",
    platform="linux/arm64",
)

FastImageBuilder()._build_image(image_spec, push=False)
