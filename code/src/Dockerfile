# Permite trocar a imagem base via docker-compose (padrão: versão CPU)
ARG BASE_IMAGE=tensorflow/tensorflow:2.15.0
FROM ${BASE_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /workspace

COPY requirements.txt /tmp/requirements.txt

# Instalação limpa sem salvar cache do pip no disco
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt