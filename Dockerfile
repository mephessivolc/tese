FROM debian:stable-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    make \
    sudo \
    bash \
    procps \
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

# Usuário padrão para Dev Containers / VS Code Server
RUN useradd -m -s /bin/bash -u 1000 vscode \
    && echo "vscode ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/vscode \
    && chmod 0440 /etc/sudoers.d/vscode \
    && mkdir -p /workspace \
               /home/vscode/.vscode-server \
               /home/vscode/.cache \
               /texlive-cache/texmf-var \
               /texlive-cache/texmf-cache \
    && chown -R vscode:vscode /workspace /home/vscode /texlive-cache

ENV HOME=/home/vscode
ENV TEXMFVAR=/texlive-cache/texmf-var
ENV TEXMFCACHE=/texlive-cache/texmf-cache

WORKDIR /workspace
USER vscode

CMD ["/bin/bash"]