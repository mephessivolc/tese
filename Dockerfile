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
    biber \
    latexmk \
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

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

RUN useradd -m -s /bin/bash -u 1000 vscode \
    && echo "vscode ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/vscode \
    && chmod 0440 /etc/sudoers.d/vscode \
    && mkdir -p /workspace \
               /texlive-cache/texmf-var \
               /texlive-cache/texmf-cache \
    && chown -R vscode:vscode /workspace /texlive-cache /home/vscode

ENV HOME=/home/vscode
ENV TEXMFVAR=/texlive-cache/texmf-var
ENV TEXMFCACHE=/texlive-cache/texmf-cache

WORKDIR /workspace
USER vscode

CMD ["/bin/bash"]