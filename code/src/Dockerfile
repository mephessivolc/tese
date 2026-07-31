# syntax=docker/dockerfile:1.7

# Imagem oficial do TensorFlow (suporta tanto CPU quanto GPU)
FROM tensorflow/tensorflow:latest-gpu

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

# Instalação de utilitários básicos de desenvolvimento
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        build-essential \
        curl \
        git \
        procps \
        sudo \
    && rm -rf /var/lib/apt/lists/*

# Criação do usuário não-root compatível com as permissões do host
RUN groupadd --gid "${USER_GID}" "${USERNAME}" \
    && useradd --uid "${USER_UID}" --gid "${USER_GID}" -m -s /bin/bash "${USERNAME}" \
    && usermod -aG sudo "${USERNAME}" \
    && echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > "/etc/sudoers.d/${USERNAME}" \
    && chmod 0440 "/etc/sudoers.d/${USERNAME}"

# Criação do ambiente virtual isolado
RUN python3 -m venv "${VIRTUAL_ENV}" \
    && chown -R "${USER_UID}:${USER_GID}" "${VIRTUAL_ENV}"

WORKDIR /workspace

# Copia e instalação de dependências
COPY requirements.txt requirements.txt

RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install -r requirements.txt

COPY . /workspace/

USER ${USERNAME}

CMD ["sleep", "infinity"]