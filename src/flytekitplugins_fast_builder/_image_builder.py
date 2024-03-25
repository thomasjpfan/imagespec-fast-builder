import shutil
from typing import List
import subprocess
import tempfile
from pathlib import Path
from string import Template
import click

from flytekit.image_spec.image_spec import (
    ImageBuildEngine,
    ImageSpecBuilder,
    ImageSpec,
)

DOCKER_FILE_TEMPLATE = Template("""\
#syntax=docker/dockerfile:1.5
FROM thomasjpfan/fast-builder-base:0.0.1 as build

RUN --mount=type=cache,target=/opt/conda/pkgs,id=conda \
    mamba create \
        -c conda-forge $CONDA_CHANNELS \
        -n dev -y python=$PYTHON_VERSION $CONDA_PACKAGES

RUN --mount=type=cache,target=/root/.cache/uv,id=uv \
    /root/.cargo/bin/uv \
    pip install --python /opt/conda/envs/dev/bin/python $PIP_INDEX \
    $PYTHON_PACKAGES

RUN /opt/conda/bin/conda-pack -n dev -o /tmp/env.tar && \
    mkdir /venv && cd /venv && tar xf /tmp/env.tar && \
    rm /tmp/env.tar

RUN /venv/bin/conda-unpack

FROM $BASE_IMAGE AS runtime

COPY --from=build /venv /venv

RUN echo "source /venv/bin/activate" >> ~/.bashrc
SHELL ["/bin/bash", "-c"]

WORKDIR /root
ENV PYTHONPATH /root
ENV FLYTE_SDK_RICH_TRACEBACKS 0

RUN useradd -u 1000 flytekit \
    && chown flytekit: /root \
    && chown flytekit: /home

USER flytekit
""")
# source_root: Optional[str] = None
# env: Optional[typing.Dict[str, str]] = None
# requirements: Optional[str] = None
# apt_packages: Optional[List[str]] = None

# cuda: Optional[str] = None
# cudnn: Optional[str] = None
# registry_config: Optional[str] = None
# commands: Optional[List[str]] = None


def write_dockerfile(image_spec: ImageSpec, tmp_dir: Path):
    base_image = image_spec.base_image or "debian:bookworm-slim"
    pip_index = f"--index-url {image_spec.pip_index}" if image_spec.pip_index else ""

    requirements_path = tmp_dir / "requirements.txt"
    if image_spec.requirements:
        shutil.copyfile(image_spec.requirements, requirements_path)
    else:
        requirements_path.touch()

    # Add packages to requirements

    docker_content = DOCKER_FILE_TEMPLATE.substitute(
        PYTHON_VERSION=image_spec.python_version,
        PYTHON_PACKAGES=" ".join(image_spec.packages),
        CONDA_PACKAGES=" ".join(image_spec.conda_packages),
        CONDA_CHANNELS="-c ".join(image_spec.conda_channels),
        BASE_IMAGE=base_image,
        PIP_INDEX=pip_index,
    )

    dockerfile_path = tmp_dir / "Dockerfile"
    dockerfile_path.write_text(docker_content)


class FastImageBuilder(ImageSpecBuilder):
    """Image builder using Docker and buildkit."""

    _SUPPORTED_OPTIONS = []

    def build_image(self, image_spec: ImageSpec) -> str:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            dockerfile_path = tmp_path / "Dockerfile"

            write_dockerfile(image_spec, dockerfile_path)

            command = [
                "docker",
                "image",
                "build",
                "--tag",
                f"{image_spec.image_name()}-fast",
                "--platform",
                image_spec.platform,
                tmp_dir,
            ]
            concat_command = " ".join()
            click.secho(f"Run command: {concat_command} ", fg="blue")
            subprocess.run(command, check=True)


# ImageBuildEngine.register("fast-builder", FastImageBuilder())
