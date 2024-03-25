import argparse

from flytekit import ImageSpec
from flytekitplugins.envd import EnvdImageSpecBuilder
from imagespec_fast_builder import FastImageBuilder

image_spec = ImageSpec(
    name="flyte_playground",
    packages=["numpy", "scipy"],
    registry="ghcr.io/thomasjpfan",
)

parser = argparse.ArgumentParser()
parser.add_argument("builder", choices=["envd", "fast-builder"])

args = parser.parse_args()

if args.builder == "envd":
    envd_builder = EnvdImageSpecBuilder()
else:
    builder = FastImageBuilder()

builder.build_image(image_spec)
