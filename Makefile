SERVICE := latex
DC := docker compose
OUTDIR := build
MAIN_NAME := main
PROJECT_PATH := 69931ba0bcdd82709908e2e5


export UID := $(shell id -u)
export GID := $(shell id -g)

LATEXMK := latexmk
LATEXMK_OPTS := -cd -pdf -synctex=1 -interaction=nonstopmode -halt-on-error -file-line-error -f

# Descobre onde está o main.tex (procura até 3 níveis)
MAIN_PATH := $(shell find . -maxdepth 3 -name "$(MAIN_NAME).tex" -print -quit)

# Diretório do main.tex
PROJECT_DIR := $(dir $(MAIN_PATH))

.PHONY: build pdf clean distclean shell sync github-pull github-push overleaf-pull overleaf-push

build:
	$(DC) build $(SERVICE)

pdf:
	@test -n "$(MAIN_PATH)" || (echo "Erro: main.tex não encontrado."; exit 2)
	$(DC) run --rm $(SERVICE) sh -lc '\
		set -e; \
		cd "$(PROJECT_DIR)"; \
		mkdir -p "../$(OUTDIR)/$(PROJECT_DIR)"; \
		find . -maxdepth 1 -type d -not -name "." -exec mkdir -p "../$(OUTDIR)/$(PROJECT_DIR)/{}" \; ; \
		$(LATEXMK) $(LATEXMK_OPTS) -outdir="../$(OUTDIR)/$(PROJECT_DIR)" "$(MAIN_NAME).tex"; \
		cp -f "../$(OUTDIR)/$(PROJECT_DIR)/$(MAIN_NAME).pdf" "../$(MAIN_NAME).pdf"'

clean:
	@test -n "$(MAIN_PATH)" || (echo "Erro: main.tex não encontrado."; exit 2)
	$(DC) run --rm $(SERVICE) sh -lc '\
		cd "$(PROJECT_DIR)" && \
		$(LATEXMK) -c -cd -outdir="../$(OUTDIR)/$(PROJECT_DIR)" "$(MAIN_NAME).tex" || true'

distclean: clean
	@rm -rf $(OUTDIR)
	@rm -f $(MAIN_NAME).pdf

shell:
	$(DC) run --rm $(SERVICE) bash

# ===== Git remotes =====
GITHUB_REMOTE   ?= origin
OVERLEAF_REMOTE ?= overleaf
GIT_BRANCH      ?= main

github-pull:
	git pull $(GITHUB_REMOTE) $(GIT_BRANCH)

github-push:
	git push $(GITHUB_REMOTE) $(GIT_BRANCH)

overleaf-pull:
	git subtree pull --prefix=$(PROJECT_PATH) overleaf master --squash

overleaf-push:
	git subtree push --prefix=$(PROJECT_PATH) overleaf master

sync: github-pull overleaf-pull github-push overleaf-push
