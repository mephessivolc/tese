# syntax=docker/dockerfile:1

FROM python:3.10-bullseye AS base

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    git \
    make \
    sudo \
    procps \
    build-essential \
    wget \
    unzip \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip jupyterlab

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm -f /tmp/requirements.txt

ARG USERNAME=clovis-caface
ARG USER_UID=1000
ARG USER_GID=1000

RUN groupadd --gid ${USER_GID} ${USERNAME} \
    && useradd -m -s /bin/bash -u ${USER_UID} -g ${USER_GID} ${USERNAME} \
    && echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/${USERNAME} \
    && chmod 0440 /etc/sudoers.d/${USERNAME} \
    && mkdir -p /workspace \
    && chown -R ${USERNAME}:${USERNAME} /workspace /home/${USERNAME}

ENV APP_USER=${USERNAME} \
    HOME=/home/${USERNAME}

WORKDIR /workspace

FROM base AS dev

RUN apt-get update && apt-get install -y --no-install-recommends \
    perl \
    biber \
    latexmk \
    texlive-base \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-latex-extra \
    texlive-pictures \
    texlive-fonts-recommended \
    texlive-lang-portuguese \
    texlive-publishers \
    texlive-bibtex-extra \
    texlive-science \
    lmodern \
 && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /texlive-cache/texmf-var /texlive-cache/texmf-cache \
    && chown -R ${APP_USER}:${APP_USER} /texlive-cache

ENV TEXMFVAR=/texlive-cache/texmf-var \
    TEXMFCACHE=/texlive-cache/texmf-cache

USER ${APP_USER}
CMD ["/bin/bash"]

FROM base AS prod

USER ${APP_USER}
CMD ["/bin/bash"]
