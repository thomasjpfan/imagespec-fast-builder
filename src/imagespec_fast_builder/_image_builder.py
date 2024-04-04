import shutil
import subprocess
import sys
import tempfile
import warnings
from pathlib import Path
from string import Template
from typing import ClassVar

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

APT_INSTALL_COMMAND_TEMPLATE = Template(
    """\
RUN --mount=type=cache,target=/var/cache/apt,id=apt \
    apt-get update && apt-get install -y --no-install-recommends \
    $APT_PACKAGES
"""
)

DOCKER_FILE_TEMPLATE = Template(
    """\
#syntax=docker/dockerfile:1.5
FROM thomasjpfan/fast-builder-base:0.0.1 as build

RUN --mount=type=cache,target=/opt/conda/pkgs,id=conda \
    mamba create \
        -c conda-forge $CONDA_CHANNELS \
        -n dev -y python=$PYTHON_VERSION $CONDA_PACKAGES

WORKDIR /root

$COPY_COMMAND

$PYTHON_INSTALL_COMMAND

RUN /opt/conda/bin/conda-pack -n dev -o /tmp/env.tar && \
    mkdir /venv && cd /venv && tar xf /tmp/env.tar && \
    rm /tmp/env.tar

RUN /venv/bin/conda-unpack

FROM $BASE_IMAGE AS runtime

RUN --mount=type=cache,target=/var/cache/apt,id=apt \
    apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates
RUN update-ca-certificates

$APT_INSTALL_COMMAND

COPY --from=build /venv /venv
ENV PATH="/venv/bin:$$PATH"

WORKDIR /root
ENV PYTHONPATH=/root FLYTE_SDK_RICH_TRACEBACKS=0 SSL_CERT_DIR=/etc/ssl/certs $ENV

$RUN_COMMANDS

RUN useradd --create-home --shell /bin/bash -u 1000 flytekit \
    && chown flytekit: /root \
    && chown flytekit: /home

RUN echo "source /venv/bin/activate" >> /home/flytekit/.bashrc
SHELL ["/bin/bash", "-c"]

USER flytekit

$COPY_COMMAND
"""
)


def write_dockerfile(image_spec: ImageSpec, tmp_dir: Path):
    base_image = image_spec.base_image or "debian:bookworm-slim"
    pip_index = f"--index-url {image_spec.pip_index}" if image_spec.pip_index else ""

    requirements = ["flytekit"]
    if image_spec.requirements:
        with open(image_spec.requirements) as f:
            requirements.extend([line.strip() for line in f.readlines()])

    if image_spec.packages:
        requirements.extend(image_spec.packages)

    requirements_path = tmp_dir / "requirements.txt"
    requirements_path.write_text("\n".join(requirements))
    python_install_command = PYTHON_INSTALL_COMMAND

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

    conda_packages = image_spec.conda_packages or []
    if image_spec.cuda:
        conda_packages.append(f"cuda={image_spec.cuda}")

    if image_spec.cudnn:
        conda_packages.append(f"cudnn={image_spec.cudnn}")

    if conda_packages:
        conda_packages_concat = " ".join(conda_packages)
    else:
        conda_packages_concat = ""

    if image_spec.conda_channels:
        conda_channels = " ".join(
            f"-c {channel}" for channel in image_spec.conda_channels
        )
    else:
        conda_channels = ""

    if image_spec.python_version:
        python_version = image_spec.python_version
    else:
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"

    if image_spec.commands:
        run_commands = "\n".join(f"RUN {command}" for command in image_spec.commands)
    else:
        run_commands = ""

    docker_content = DOCKER_FILE_TEMPLATE.substitute(
        PYTHON_VERSION=python_version,
        PYTHON_INSTALL_COMMAND=python_install_command,
        CONDA_PACKAGES=conda_packages_concat,
        CONDA_CHANNELS=conda_channels,
        APT_INSTALL_COMMAND=apt_install_command,
        BASE_IMAGE=base_image,
        PIP_INDEX=pip_index,
        ENV=env,
        COPY_COMMAND=copy_command,
        RUN_COMMANDS=run_commands,
    )

    dockerfile_path = tmp_dir / "Dockerfile"
    dockerfile_path.write_text(docker_content)


class FastImageBuilder(ImageSpecBuilder):
    """Image builder using Docker and buildkit."""

    _SUPPORTED_IMAGE_SPEC_PARAMETERS: ClassVar[set] = {
        "name",
        "python_version",
        "builder",
        "source_root",
        "env",
        "registry",
        "packages",
        "conda_packages",
        "conda_channels",
        "requirements",
        "apt_packages",
        "platform",
        "cuda",
        "cudnn",
        "base_image",
        "pip_index",
        # "registry_config",
        "commands",
    }

    def build_image(self, image_spec: ImageSpec) -> str:
        return self._build_image(image_spec)

    def _build_image(self, image_spec: ImageSpec, *, push: bool = True) -> str:
        # For testing, set `push=False`` to just build the image locally and not push to
        # registry
        unsupported_parameters = [
            name
            for name, value in vars(image_spec).items()
            if value is not None
            and name not in self._SUPPORTED_IMAGE_SPEC_PARAMETERS
            and not name.startswith("_")
        ]
        if unsupported_parameters:
            msg = (
                f"The following parameters are unsupported and ignored: "
                f"{unsupported_parameters}"
            )
            warnings.warn(msg, UserWarning, stacklevel=2)

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

            if image_spec.registry and push:
                command.append("--push")
            command.append(tmp_dir)

            concat_command = " ".join(command)
            click.secho(f"Run command: {concat_command} ", fg="blue")
            subprocess.run(command, check=True)


ImageBuildEngine.register("fast-builder", FastImageBuilder())
