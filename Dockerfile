# syntax=docker/dockerfile:1.7

FROM python:3.10-slim-bookworm AS python-base

ARG USERNAME=devuser
ARG USER_UID=1000
ARG USER_GID=1000

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLCONFIGDIR=/tmp/matplotlib \
    PYTHONPATH=/workspace/python:/workspace/python/src:/workspace

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
        tini \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid "${USER_GID}" "${USERNAME}" \
    && useradd --uid "${USER_UID}" --gid "${USER_GID}" -m -s /bin/bash "${USERNAME}" \
    && usermod -aG sudo "${USERNAME}" \
    && echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > "/etc/sudoers.d/${USERNAME}" \
    && chmod 0440 "/etc/sudoers.d/${USERNAME}"

WORKDIR /workspace

COPY requirements.txt requirements.txt

RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt \
    && mkdir -p /tmp/matplotlib

COPY . /workspace/

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["sleep", "infinity"]


FROM python-base AS local

ARG USERNAME=devuser

ENV TEXMFVAR=/workspace/.texlive/texmf-var \
    TEXMFCACHE=/workspace/.texlive/texmf-cache

USER root

# Ambiente local: prioriza compatibilidade do LaTeX.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        biber \
        chktex \
        latexmk \
        texlive-full \
    && rm -rf /var/lib/apt/lists/*

USER ${USERNAME}


FROM python-base AS server

ARG USERNAME=devuser
USER ${USERNAME}
