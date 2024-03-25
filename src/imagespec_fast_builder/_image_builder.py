import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from string import Template

import click
from flytekit.image_spec.image_spec import (
    ImageBuildEngine,
    ImageSpec,
    ImageSpecBuilder,
)

PYTHON_INSTALL_COMMAND = """\
RUN --mount=type=cache,target=/root/.cache/uv,id=uv \
    --mount=type=bind,target=requirements.txt,src=requirements.txt \
    /root/.cargo/bin/uv \
    pip install --python /opt/conda/envs/dev/bin/python $PIP_INDEX \
    --requirement requirements.txt
"""

APT_INSTALL_COMMAND_TEMPLATE = Template("""\
RUN --mount=type=cache,target=/var/cache/apt,id=apt \
    apt-get update && apt-get install -y \
    $APT_PACKAGES
""")

DOCKER_FILE_TEMPLATE = Template(
    """\
#syntax=docker/dockerfile:1.5
FROM thomasjpfan/fast-builder-base:0.0.1 as build

RUN --mount=type=cache,target=/opt/conda/pkgs,id=conda \
    mamba create \
        -c conda-forge $CONDA_CHANNELS \
        -n dev -y python=$PYTHON_VERSION $CONDA_PACKAGES

$PYTHON_INSTALL_COMMAND

RUN /opt/conda/bin/conda-pack -n dev -o /tmp/env.tar && \
    mkdir /venv && cd /venv && tar xf /tmp/env.tar && \
    rm /tmp/env.tar

RUN /venv/bin/conda-unpack

FROM $BASE_IMAGE AS runtime

$APT_INSTALL_COMMAND

COPY --from=build /venv /venv
ENV PATH="/venv/bin:$$PATH"

WORKDIR /root
ENV PYTHONPATH=/root FLYTE_SDK_RICH_TRACEBACKS=0 $ENV

RUN useradd -u 1000 flytekit \
    && chown flytekit: /root \
    && chown flytekit: /home \
    && mkdir /home/flytekit

RUN echo "source /venv/bin/activate" >> /home/flytekit/.bashrc
SHELL ["/bin/bash", "-c"]

USER flytekit

$COPY_COMMAND
"""
)
# TODO: Add support for the following
# cuda: Optional[str] = None
# cudnn: Optional[str] = None
# registry_config: Optional[str] = None
# commands: Optional[List[str]] = None


def write_dockerfile(image_spec: ImageSpec, tmp_dir: Path):
    base_image = image_spec.base_image or "debian:bookworm-slim"
    pip_index = f"--index-url {image_spec.pip_index}" if image_spec.pip_index else ""

    requirements = ["flytekit"]
    if image_spec.requirements:
        with open(image_spec.requirements) as f:
            requirements.extend([line.strip() for line in f.readlines()])
    requirements.extend(image_spec.packages)

    if requirements:
        requirements_path = tmp_dir / "requirements.txt"
        requirements_path.write_text("\n".join(requirements))
        python_install_command = PYTHON_INSTALL_COMMAND
    else:
        python_install_command = ""

    if image_spec.env:
        env = " ".join(f"{k}={v}" for k, v in image_spec.env.items())
    else:
        env = ""

    if image_spec.apt_packages:
        apt_install_command = APT_INSTALL_COMMAND_TEMPLATE.substitute(
            APT_PACKAGES=" ".join(image_spec.apt_packages)
        )
    else:
        apt_install_command = ""

    if image_spec.source_root:
        source_path = tmp_dir / "src"
        shutil.copytree(image_spec.source_root, source_path)
        copy_command = "COPY ./src /root"
    else:
        copy_command = ""

    if image_spec.conda_packages:
        conda_packages = " ".join(image_spec.conda_packages)
    else:
        conda_packages = ""

    if image_spec.conda_channels:
        conda_channels = "-c ".join(image_spec.conda_channels)
    else:
        conda_channels = ""

    if image_spec.python_version:
        python_version = image_spec.python_version
    else:
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"

    docker_content = DOCKER_FILE_TEMPLATE.substitute(
        PYTHON_VERSION=python_version,
        PYTHON_INSTALL_COMMAND=python_install_command,
        CONDA_PACKAGES=conda_packages,
        CONDA_CHANNELS=conda_channels,
        APT_INSTALL_COMMAND=apt_install_command,
        BASE_IMAGE=base_image,
        PIP_INDEX=pip_index,
        ENV=env,
        COPY_COMMAND=copy_command,
    )

    dockerfile_path = tmp_dir / "Dockerfile"
    dockerfile_path.write_text(docker_content)


class FastImageBuilder(ImageSpecBuilder):
    """Image builder using Docker and buildkit."""

    def build_image(self, image_spec: ImageSpec) -> str:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            write_dockerfile(image_spec, tmp_path)

            command = [
                "docker",
                "image",
                "build",
                "--tag",
                f"{image_spec.image_name()}",
                "--platform",
                image_spec.platform,
            ]

            if image_spec.registry:
                command.append("--push")
            command.append(tmp_dir)

            concat_command = " ".join(command)
            click.secho(f"Run command: {concat_command} ", fg="blue")
            subprocess.run(command, check=True)


ImageBuildEngine.register("fast-builder", FastImageBuilder())
