from flytekit import ImageSpec
from flytekitplugins.envd import EnvdImageSpecBuilder
from imagespec_fast_builder import FastImageBuilder

image_spec = ImageSpec(
    name="flyte_playground",
    packages=["numpy", "scipy"],
    source_root="dockerfiles",
    registry="ghcr.io/thomasjpfan",
)

# envd_builder = EnvdImageSpecBuilder()
# envd_builder.build_image(image_spec)

builder = FastImageBuilder()
builder.build_image(image_spec)
