from flytekit import ImageSpec
from imagespec_fast_builder import FastImageBuilder

folding_img = ImageSpec(
    name="unionbio-protein",
    python_version="3.11",
    packages=["numpy"],
    # conda_channels=["bioconda", "conda-forge"],
    # conda_packages=["prodigal", "biotite", "biopython", "py3Dmol"],
    # registry="ghcr.io/unionai-oss",
    # platform="linux/amd64",
)

FastImageBuilder()._build_image(folding_img, push=False)
