FROM python:3.10-bullseye

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

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

RUN pip install --upgrade pip
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

ARG USERNAME=clovis-caface
ARG USER_UID=1000
ARG USER_GID=1000

RUN groupadd --gid ${USER_GID} ${USERNAME} \
    && useradd -m -s /bin/bash -u ${USER_UID} -g ${USER_GID} ${USERNAME} \
    && echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/${USERNAME} \
    && chmod 0440 /etc/sudoers.d/${USERNAME} \
    && mkdir -p /workspace \
               /texlive-cache/texmf-var \
               /texlive-cache/texmf-cache \
    && chown -R ${USERNAME}:${USERNAME} /workspace /texlive-cache /home/${USERNAME}

ENV HOME=/home/clovis-caface
ENV TEXMFVAR=/texlive-cache/texmf-var
ENV TEXMFCACHE=/texlive-cache/texmf-cache

WORKDIR /workspace
USER clovis-caface

CMD ["/bin/bash"]