# Code Companion — dev tasks. Run `make` (or `make help`) to list them.

help:
	@echo "targets: setup install run  py-check py-fix check fix  ext-install ext-build ext-check"

# ── Setup / run ───────────────────────────────────────────────────────────────
setup: hooks install        # first-time: git hooks + dependencies

hooks:
	git config core.hooksPath .githooks

install:
	pip install -r requirements.txt -r requirements.dev.txt

run:
	uvicorn app.main:app --reload

# ── Python — lint, format, typecheck ──────────────────────────────────────────
py-check:
	ruff check app/
	ruff format --check app/
	mypy app/

py-fix:
	ruff check --fix app/
	ruff format app/

# ── Extension — install, build, typecheck ─────────────────────────────────────
ext-install:
	cd extension && npm install

ext-build:
	cd extension && npm run compile

ext-check:
	cd extension && npm run check

# ── Run everything (backend only for now — extension has no deps installed) ────
check: py-check
fix: py-fix
