# ===== Project configuration =====
PROJECT_PATH := 69931ba0bcdd82709908e2e5

# ===== Git remotes =====
GITHUB_REMOTE   ?= origin
OVERLEAF_REMOTE ?= overleaf

# ===== Branches =====
GIT_BRANCH      ?= main
OVERLEAF_BRANCH ?= master

.PHONY: \
	status log remotes branch \
	commit-update \
	github-pull github-push \
	overleaf-pull overleaf-push \
	sync sync-github sync-overleaf \
	publish-github publish-overleaf publish-all

# ===== Basic repository info =====
status:
	git status

log:
	git --no-pager log --oneline --graph --decorate -n 10

remotes:
	git remote -v

branch:
	git branch --show-current

# ===== Add + commit with automatic datetime =====
commit-update:
	mv $(PROJECT_PATH)/build/main.pdf $(PROJECT_PATH)
	git add -A
	git commit -m "update $$(date '+%Y-%m-%d %H:%M:%S')" || echo "Nothing to commit"

# ===== GitHub operations =====
github-pull:
	git pull $(GITHUB_REMOTE) $(GIT_BRANCH)

github-push:
	git push $(GITHUB_REMOTE) $(GIT_BRANCH)

# ===== Overleaf operations =====
overleaf-pull:
	git subtree pull --prefix=$(PROJECT_PATH) $(OVERLEAF_REMOTE) $(OVERLEAF_BRANCH) --squash

overleaf-push:
	git subtree push --prefix=$(PROJECT_PATH) $(OVERLEAF_REMOTE) $(OVERLEAF_BRANCH)

# ===== Safer sync flow =====
# Atualiza primeiro a branch local com GitHub e depois traz as mudanças do Overleaf.
# Se houver conflito, o processo para antes de qualquer push.
sync: github-pull overleaf-pull
	@echo "Sync local concluído. Revise com 'make status' e envie com 'make sync-github' e/ou 'make sync-overleaf'."

# Envio explícito, separado, para evitar propagar conflitos sem revisão
sync-github:
	git push $(GITHUB_REMOTE) $(GIT_BRANCH)

sync-overleaf:
	git subtree push --prefix=$(PROJECT_PATH) $(OVERLEAF_REMOTE) $(OVERLEAF_BRANCH)

# ===== Commit + push helpers =====
publish-github: commit-update github-push

publish-overleaf: commit-update overleaf-push

publish-all: commit-update github-push overleaf-push