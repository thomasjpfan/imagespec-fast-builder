from flytekit import ImageSpec

from imagespec_fast_builder import FastImageBuilder
from flytekit.image_spec.image_spec import ImageBuildEngine

folding_img = ImageSpec(
    name="unionbio-protein",
    python_version="3.11",
    packages=["numpy"],
    # conda_channels=["bioconda", "conda-forge"],
    # conda_packages=["prodigal", "biotite", "biopython", "py3Dmol"],
    # registry="ghcr.io/unionai-oss",
    # platform="linux/amd64",
)
# Generic way to build an image, if registry is set, then the image is automatically pushed
# ImageBuildEngine().build(image_spec)

# My image builder has a private not push command
FastImageBuilder()._build_image(folding_img, push=False)
