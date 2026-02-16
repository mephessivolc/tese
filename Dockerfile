FROM debian:stable-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates git make \
    latexmk \
    texlive-latex-base texlive-latex-recommended texlive-latex-extra \
    texlive-pictures \
    texlive-fonts-recommended \
    lmodern \
    texlive-lang-portuguese \
    texlive-publishers \
    texlive-bibtex-extra \
    texlive-science \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
