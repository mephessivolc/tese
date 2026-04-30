# syntax=docker/dockerfile:1.7

FROM python:3.10-slim-bookworm AS python-base

ARG USERNAME=clovis-caface
ARG USER_UID=1000
ARG USER_GID=1000

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/workspace:/workspace/code:/workspace/code/src \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        build-essential \
        ca-certificates \
        curl \
        git \
        less \
        openssh-client \
        procps \
        sudo \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid "${USER_GID}" "${USERNAME}" \
    && useradd --uid "${USER_UID}" --gid "${USER_GID}" -m -s /bin/bash "${USERNAME}" \
    && usermod -aG sudo "${USERNAME}" \
    && echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > "/etc/sudoers.d/${USERNAME}" \
    && chmod 0440 "/etc/sudoers.d/${USERNAME}" \
    && install -d -o "${USER_UID}" -g "${USER_GID}" "/home/${USERNAME}/.cache/matplotlib"

RUN python -m venv "${VIRTUAL_ENV}" \
    && chown -R "${USER_UID}:${USER_GID}" "${VIRTUAL_ENV}"

WORKDIR /workspace

COPY requirements.txt /tmp/requirements.txt

RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install -r /tmp/requirements.txt \
    && python -c "import numpy; print('numpy ok:', numpy.__version__)"

COPY . /workspace/

FROM python-base AS local

ARG USERNAME=devuser

ENV TEXMFVAR=/workspace/.texlive/texmf-var \
    TEXMFCACHE=/workspace/.texlive/texmf-cache \
    MPLCONFIGDIR=/home/${USERNAME}/.cache/matplotlib

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        biber \
        chktex \
        latexmk \
        texlive-full \
    && rm -rf /var/lib/apt/lists/*

USER ${USERNAME}

CMD ["sleep", "infinity"]

FROM python-base AS server

ARG USERNAME=devuser

ENV MPLCONFIGDIR=/home/${USERNAME}/.cache/matplotlib

USER ${USERNAME}

CMD ["python", "/workspace/code/src/teste.py"]