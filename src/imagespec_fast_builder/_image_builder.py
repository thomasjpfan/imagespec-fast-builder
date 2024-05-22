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
    _F_IMG_ID,
    ImageBuildEngine,
    ImageSpec,
    ImageSpecBuilder,
)

PYTHON_INSTALL_COMMAND_TEMPLATE = Template("""\
RUN --mount=type=cache,sharing=locked,mode=0777,target=/root/.cache/uv,id=uv \
    --mount=type=bind,target=requirements.txt,src=requirements.txt \
    /opt/conda/envs/uv/bin/uv \
    pip install --python /opt/conda/envs/dev/bin/python $PIP_INDEX \
    --requirement requirements.txt
""")

APT_INSTALL_COMMAND_TEMPLATE = Template(
    """\
RUN --mount=type=cache,sharing=locked,mode=0777,target=/var/cache/apt,id=apt \
    apt-get update && apt-get install -y --no-install-recommends \
    $APT_PACKAGES
"""
)

DOCKER_FILE_TEMPLATE = Template(
    """\
#syntax=docker/dockerfile:1.5
FROM $BASE_IMAGE

$APT_INSTALL_COMMAND
RUN update-ca-certificates

RUN useradd --create-home --shell /bin/bash flytekit \
    && chown -R flytekit /root \
    && chown -R flytekit /home

ENV MAMBA_BIN_DIR=/opt/conda/bin MAMBA_VERSION=1.5.8 MAMBA_ROOT_PREFIX=/opt/conda
RUN /bin/bash -c 'set -euo pipefail && \
    ARCH="$$(uname -m)" && \
    if [[ "$$ARCH" == "aarch64" ]]; then \
    ARCH="aarch64"; \
    elif [[ "$$ARCH" == "ppc64le" ]]; then \
    ARCH="ppc64le"; \
    else \
    ARCH="64"; \
    fi && \
    mkdir -p $$MAMBA_BIN_DIR && \
    curl -Ls https://micro.mamba.pm/api/micromamba/linux-$$ARCH/$$MAMBA_VERSION | \
    tar -xvj -C $$MAMBA_BIN_DIR --strip-components=1 bin/micromamba' && \
    chown -R flytekit $$MAMBA_ROOT_PREFIX

RUN --mount=type=cache,sharing=locked,mode=0777,target=/opt/conda/pkgs,id=conda \
    /opt/conda/bin/micromamba create -n uv uv -c conda-forge

RUN --mount=type=cache,sharing=locked,mode=0777,target=/opt/conda/pkgs,id=conda \
    /opt/conda/bin/micromamba create -n dev -c conda-forge \
    python=$PYTHON_VERSION $CONDA_PACKAGES

$PYTHON_INSTALL_COMMAND

# Configure user space
ENV PATH="/opt/conda/envs/dev/bin:/opt/conda/envs/uv/bin:/opt/conda/bin:$$PATH"
ENV FLYTE_SDK_RICH_TRACEBACKS=0 SSL_CERT_DIR=/etc/ssl/certs $ENV

$COPY_COMMAND_RUNTIME
$RUN_COMMANDS

WORKDIR /root
SHELL ["/bin/bash", "-c"]

USER flytekit
"""
)


def create_docker_context(image_spec: ImageSpec, tmp_dir: Path):
    """Populate tmp_dir with Dockerfile as specified by the `image_spec`."""
    base_image = image_spec.base_image or "debian:bookworm-slim"

    requirements = ["flytekit"]
    if image_spec.requirements:
        with open(image_spec.requirements) as f:
            requirements.extend([line.strip() for line in f.readlines()])

    if image_spec.packages:
        requirements.extend(image_spec.packages)

    requirements_path = tmp_dir / "requirements.txt"
    requirements_path.write_text("\n".join(requirements))

    pip_index = f"--index-url {image_spec.pip_index}" if image_spec.pip_index else ""
    python_install_command = PYTHON_INSTALL_COMMAND_TEMPLATE.substitute(
        PIP_INDEX=pip_index
    )
    env_dict = {"PYTHONPATH": "/root", _F_IMG_ID: image_spec.image_name()}

    if image_spec.env:
        env_dict.update(image_spec.env)

    env = " ".join(f"{k}={v}" for k, v in env_dict.items())

    apt_packages = ["ca-certificates", "bzip2", "curl"]
    if image_spec.apt_packages:
        apt_packages.extend(image_spec.apt_packages)

    apt_install_command = APT_INSTALL_COMMAND_TEMPLATE.substitute(
        APT_PACKAGES=" ".join(apt_packages)
    )

    if image_spec.source_root:
        source_path = tmp_dir / "src"
        shutil.copytree(image_spec.source_root, source_path)
        copy_command_runtime = "COPY --chown=flytekit ./src /root"
    else:
        copy_command_runtime = ""

    conda_packages = image_spec.conda_packages or []
    conda_channels = image_spec.conda_channels or []

    if image_spec.cuda:
        conda_packages.append(f"cuda={image_spec.cuda}")
        if image_spec.cudnn:
            conda_packages.append(f"cudnn={image_spec.cudnn}")

    if conda_packages:
        conda_packages_concat = " ".join(conda_packages)
    else:
        conda_packages_concat = ""

    if conda_channels:
        conda_channels_concat = " ".join(f"-c {channel}" for channel in conda_channels)
    else:
        conda_channels_concat = ""

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
        CONDA_CHANNELS=conda_channels_concat,
        APT_INSTALL_COMMAND=apt_install_command,
        BASE_IMAGE=base_image,
        PIP_INDEX=pip_index,
        ENV=env,
        COPY_COMMAND_RUNTIME=copy_command_runtime,
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
            create_docker_context(image_spec, tmp_path)

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


ImageBuildEngine.register("fast-builder", FastImageBuilder(), priority=8)
