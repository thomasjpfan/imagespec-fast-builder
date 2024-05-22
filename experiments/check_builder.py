from flytekit import ImageSpec

from imagespec_fast_builder import FastImageBuilder
from flytekit.image_spec.image_spec import ImageBuildEngine

test_img = ImageSpec(
    name="test_image",
    base_image="ubuntu:24.04",
    python_version="3.11",
    packages=["flytekit"],
    # apt_packages=["git"],
    conda_packages=[  # 2
        "requests",
        "numpy==1.26.4",
        "pandas",
        "keras",
        "pytorch",
        "seaborn",
        "matplotlib",
    ],
    builder="fast-builder",
    registry="localhost:30000",
    platform="linux/amd64",
)

# Generic way to build an image, if registry is set, then the image is automatically pushed
# ImageBuildEngine().build(image_spec)

# My image builder has a private not push command
FastImageBuilder()._build_image(test_img, push=False)
