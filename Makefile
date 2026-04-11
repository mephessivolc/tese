SHELL := /bin/bash
.DEFAULT_GOAL := help

# ===== Project paths =====
PROJECT_PATH        ?= EscritaTese
PROJECT_BUILD_PATH  ?= $(PROJECT_PATH)/build
PROJECT_PDF_FILE    ?= main.pdf
PROJECT_PDF_SRC     := $(PROJECT_BUILD_PATH)/$(PROJECT_PDF_FILE)
PROJECT_PDF_DST     := $(PROJECT_PATH)/$(PROJECT_PDF_FILE)
CODE_PATH           ?= code

# ===== Remotes =====
GITHUB_REMOTE       ?= origin
OVERLEAF_REMOTE     ?= overleaf
SERVER_REMOTE       ?= server-code

# ===== Branches =====
GIT_BRANCH          ?= main
OVERLEAF_BRANCH     ?= master
SERVER_BRANCH       ?= main


# ===== Overleaf =====
OVERLEAF_PREFIX ?= EscritaTese
OVERLEAF_URL ?= https://git@git.overleaf.com/69931ba0bcdd82709908e2e5

# ===== Server =====
SERVER_SSH          ?= clovis@177.104.60.30
SERVER_WORKTREE     ?= ~/work/tese-code

.PHONY: \
	help status log remotes branch \
	update-pdf commit-all commit-writing commit-code \
	github-pull github-push \
	overleaf-pull overleaf-push \
	server-pull server-push server-ssh server-worktree-status server-worktree-pull server-deploy \
	sync-in sync-writing sync-code sync-all \
	publish-writing publish-code publish-all

help:
	@echo "Targets principais:"
	@echo "  make status              # status do repositório principal"
	@echo "  make sync-in             # traz mudancas de GitHub, Overleaf e Server"
	@echo "  make publish-writing     # commit + push para GitHub e Overleaf"
	@echo "  make publish-code        # commit + push para GitHub e Server subtree"
	@echo "  make publish-all         # commit + push para GitHub, Overleaf e Server subtree"
	@echo "  make server-deploy       # atualiza a worktree de execucao no servidor"
	@echo "  make server-worktree-status"

# ===== Basic repository info =====
status:
	git status

log:
	git --no-pager log --oneline --graph --decorate -n 10

remotes:
	git remote -v

branch:
	git branch --show-current

# ===== Helpers =====
update-pdf:
	@if [ -f "$(PROJECT_PDF_SRC)" ]; then \
		cp "$(PROJECT_PDF_SRC)" "$(PROJECT_PDF_DST)"; \
		echo "PDF atualizado em $(PROJECT_PDF_DST)"; \
	else \
		echo "PDF nao encontrado em $(PROJECT_PDF_SRC); Copia não disponivel."; \
	fi

commit-all: update-pdf
	@git add -A
	@git commit -m "update $$(date '+%Y-%m-%d %H:%M:%S')" || echo "Nothing to commit"

commit-writing: update-pdf
	@git add "$(PROJECT_PATH)"
	@git commit -m "writing update $$(date '+%Y-%m-%d %H:%M:%S')" || echo "Nothing to commit"

commit-code:
	@git add "$(CODE_PATH)"
	@git commit -m "code update $$(date '+%Y-%m-%d %H:%M:%S')" || echo "Nothing to commit"

# ===== GitHub: repo principal =====
github-pull:
	git pull $(GITHUB_REMOTE) $(GIT_BRANCH)

github-push:
	git push $(GITHUB_REMOTE) $(GIT_BRANCH)

# ===== Overleaf: subtree de EscritaTese =====

ensure-clean:
	@git diff --quiet || (echo "Erro: há modificações locais não commitadas."; git status --short; exit 1)
	@git diff --cached --quiet || (echo "Erro: há arquivos staged não commitados."; git status --short; exit 1)

overleaf-remote-set:
	@git remote get-url $(OVERLEAF_REMOTE) >/dev/null 2>&1 || git remote add $(OVERLEAF_REMOTE) $(OVERLEAF_URL)
	@git remote set-url $(OVERLEAF_REMOTE) $(OVERLEAF_URL)

overleaf-fetch: overleaf-remote-set
	git fetch $(OVERLEAF_REMOTE) $(OVERLEAF_BRANCH)

overleaf-bootstrap: ensure-clean overleaf-fetch
	git rm -r --ignore-unmatch $(OVERLEAF_PREFIX)
	rm -rf $(OVERLEAF_PREFIX)
	git commit -m "Remove $(OVERLEAF_PREFIX) local para reimportar do Overleaf" || true
	git subtree add --prefix=$(OVERLEAF_PREFIX) $(OVERLEAF_REMOTE) $(OVERLEAF_BRANCH) --squash

overleaf-pull: ensure-clean overleaf-fetch
	git subtree pull --prefix=$(OVERLEAF_PREFIX) $(OVERLEAF_REMOTE) $(OVERLEAF_BRANCH) --squash

overleaf-push: ensure-clean
	git subtree push --prefix=$(OVERLEAF_PREFIX) $(OVERLEAF_REMOTE) $(OVERLEAF_BRANCH)

# ===== Server: subtree de code/ =====
server-pull:
	git subtree pull --prefix=$(CODE_PATH) $(SERVER_REMOTE) $(SERVER_BRANCH) --squash

server-push:
	git subtree push --prefix=$(CODE_PATH) $(SERVER_REMOTE) $(SERVER_BRANCH)

server-ssh:
	ssh $(SERVER_SSH)

server-worktree-status:
	ssh $(SERVER_SSH) "cd $(SERVER_WORKTREE) && git status -sb && echo && git log --oneline -n 5"

server-worktree-pull:
	ssh $(SERVER_SSH) "cd $(SERVER_WORKTREE) && git pull origin $(SERVER_BRANCH)"

# Atualiza a copia de trabalho do servidor para executar a ultima versao enviada.
# Mantido separado de server-push para nao sobrescrever seu fluxo se houver trabalho em andamento no servidor.
server-deploy: server-push server-worktree-pull

# ===== Entrada de mudancas externas =====
# Ordem recomendada:
# 1) GitHub (repo principal)
# 2) Overleaf (subtree da escrita)
# 3) Server (subtree do codigo)
sync-in: github-pull overleaf-pull server-pull
	@echo "Sync concluido. Revise com 'make status' e publique com os targets publish-* quando quiser."

sync-writing: github-pull overleaf-pull
	@echo "GitHub + Overleaf sincronizados."

sync-code: github-pull server-pull
	@echo "GitHub + Server sincronizados."

sync-all: sync-in

# ===== Saida / publicacao =====
# GitHub recebe o projeto inteiro.
publish-writing: commit-all github-push overleaf-push

publish-code: commit-all github-push server-push

publish-all: commit-all github-push overleaf-push server-push

git remote add overleaf https://git@git.overleaf.com/69931ba0bcdd82709908e2e5 
