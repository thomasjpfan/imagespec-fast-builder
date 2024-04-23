from flytekit import ImageSpec
from imagespec_fast_builder import FastImageBuilder

image_spec = ImageSpec(
    name="flyte_playground",
    base_image="nvcr.io/nvidia/driver:535-5.15.0-1048-nvidia-ubuntu22.04",
    builder="fast-builder",
    packages=["torch==2.2.2"],
    registry="ghcr.io/thomasjpfan",
    # platform="linux/arm64",
    # cuda="12.3.2",
    # cudnn="8",
)

FastImageBuilder()._build_image(image_spec, push=False)
