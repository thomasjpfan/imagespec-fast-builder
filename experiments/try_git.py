from flytekit import ImageSpec
from imagespec_fast_builder import FastImageBuilder


comet_ml_package = "git+https://github.com/thomasjpfan/flytekit.git@thomasjpfan/cometml_init#subdirectory=plugins/flytekit-comet-ml"

image = ImageSpec(
    name="check-flytekit",
    builder="fast-builder",
    apt_packages=["git"],
    packages=[comet_ml_package, "comet-ml"],
)

builder = FastImageBuilder()
builder._build_image(image, push=False)
