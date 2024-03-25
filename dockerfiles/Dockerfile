#syntax=docker/dockerfile:1.5
# This base image is built from Dockefile.base
FROM ghcr.io/thomasjpfan/fast-builder-base:0.0.1

RUN --mount=type=cache,target=/opt/conda/pkgs,id=conda \
    mamba create -c conda-forge -n dev python=3.11 -y

RUN --mount=type=cache,target=/root/.cache/uv,id=uv \
    /root/.cargo/bin/uv pip install --python /opt/conda/envs/dev/bin/python \
    scipy joblib numpy scikit-learn

RUN /opt/conda/bin/conda-pack -n dev -o /tmp/env.tar && \
    mkdir /venv && cd /venv && tar xf /tmp/env.tar && \
    rm /tmp/env.tar

RUN /venv/bin/conda-unpack

FROM debian:bookworm-slim AS runtime

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
