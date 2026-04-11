# Uso sugerido

## Desenvolvimento local

```bash
docker compose -f compose.yaml -f compose.dev.yaml up -d --build
```

Entrar no container:

```bash
docker compose -f compose.yaml -f compose.dev.yaml exec workspace bash
```

## Ambiente do servidor

Subir só o workspace interativo:

```bash
docker compose -f compose.yaml -f compose.prod.yaml up -d --build workspace
```

Entrar no container:

```bash
docker compose -f compose.yaml -f compose.prod.yaml exec workspace bash
```

Rodar um job CPU isolado:

```bash
docker compose -f compose.yaml -f compose.prod.yaml --profile cpu run --rm sim-cpu
```

Rodar um job GPU isolado:

```bash
docker compose -f compose.yaml -f compose.prod.yaml --profile gpu run --rm sim-gpu
```

Gerar a configuração final já mesclada:

```bash
docker compose -f compose.yaml -f compose.prod.yaml config
```
