# Code Companion

An agent-first VS Code coding assistant, like Claude Code. Two parts in one repo:

- **`app/`** — FastAPI backend (Python 3.10). The engine: chat, the agent tool loop, providers, and (later, optional) retrieval.
- **`extension/`** — VS Code extension (TypeScript). The client: chat panel, commands, talks to the backend.

The build plan lives in [roadmap.md](roadmap.md) — agent-first vertical slices (Phase 0 skeleton → agent loop → edit/run → any-LLM → cheaper/faster → eval → then RAG as a measured experiment). The heart is the **agent tool loop**, not RAG; RAG is an optional, evaluated branch. The old RAG-first plan is kept for reference in [.archive/roadmap.md](.archive/roadmap.md). **We are at Phase 0:** a walking skeleton (extension ↔ FastAPI ↔ chat). `app/services/chat.py` currently returns a stub; swapping it for a real LLM call is S0.2.

This backend is also a **reusable FastAPI skeleton** — keep the core (`config`, `logging`, `constants`, `application`, middleware, exceptions) generic and project-agnostic. Project-specific code lives in `api/`, `services/`, and `models/`.

## Layout

```
app/
  main.py            create_application(): app factory + lifespan
  core/
    constants.py     BASE_DIR (repo root) — import BASE_DIR from here, never recompute; AppMode (APP/CLI)
    config.py        Settings (pydantic-settings), env via .env; import `settings`
    logging.py       RelativePathFormatter + setup_logging(mode) (dictConfig; CLI=plain stderr)
    application.py    Application(mode): process-wide lifecycle — DB (both), HTTP client (APP only)
    db.py            SQLAlchemy async Base/engine/sessionmaker
    security.py      create_token / verify_token — stateless JWT (HS256), no DB
    exceptions.py    CodeCompanionException hierarchy (incl. AuthenticationError → 401)
  api/               HTTP layer — routers only, thin. router.py aggregates (no version prefix)
  api/auth.py        @authenticated decorator: verify bearer token → request.state.user_id
  migrations/        Alembic (async env.py); versions/ holds revisions
  services/          domain logic lives here, not in views (chat, catalog, user, session)
  models/schema.py   pydantic request/response (wire) models
  models/tables.py   SQLAlchemy ORM tables (User, ChatSession, SessionMessage) — distinct from wire models
  cli/               typer admin CLI (`python -m app.cli.main`) — runs Application in CLI mode
  middleware/        request logging + exception handlers
config.yaml          LLM catalog (gitignored — holds keys); commit config.example.yaml
extension/           VS Code extension (own package.json, tsconfig, .vscode/)
```

## Conventions (backend)

- **BASE_DIR**: defined once in `app/core/constants.py` as the repo root. Import it (`from app.core.constants import BASE_DIR`) — do not write `Path(__file__).parent...` elsewhere.
- **Config**: app/infra settings (DEBUG, CORS, SECRET_KEY, DB, ports) come from `.env` via `settings` (`app.core.config`) — never `os.getenv`. **LLM/model config is separate**: it lives in `config.yaml` (gitignored, holds API keys; commit `config.example.yaml`), loaded by `app/services/catalog.py`. Clients pick a `provider`+`model` from `GET /api/models`; `catalog.resolve()` returns credentials, `max_tokens`, and the per-provider `mini_model`. Don't add LLM config to `settings`/`.env`.
- **Logging**: every module has `logger = logging.getLogger(__name__)` — never a hardcoded name. `setup_logging(mode)` runs once per process (APP in the app factory, CLI in the typer callback). Logs render as `LEVEL <iso-time>.<ms> <path>:<line> - message`, where `<path>` is relative to BASE_DIR via `RelativePathFormatter`.
- **Service layer**: domain logic goes in `app/services/`; routers only parse → call service → shape response.
- **API is unversioned** — no `/v1`. Add routers to `app/api/router.py`; they mount under `settings.API_PREFIX` (`/api`).
- **DB**: async SQLAlchemy 2.0. ORM tables in `app/models/tables.py` (inherit `Base` from `app.core.db`), never mixed with pydantic wire models in `schema.py`. Access via `Application.sessionmaker`. Schema changes go through Alembic (`migrations/`, async `env.py`, url from `settings.DATABASE_URL`); apply with `python -m app.cli.main migrate`. DB-touching CLI commands fail fast unless the schema is at head.
- **Sessions**: conversation history is server-side (not client-supplied). `ChatRequest` = `session_id` + `message` (+ optional `context`/`provider`/`model`/`effort`). `POST /api/chat` loads the thread, streams, and persists the user + assistant turns; history is compacted server-side (a char budget for now). ChatSession CRUD lives at `/api/sessions` (all authenticated, scoped to the caller). `SessionService` owns persistence + domain-message conversion.
- **Auth**: stateless signed JWT (`app.core.security`). The CLI issues tokens (`SECRET_KEY`, `TOKEN_TTL_DAYS`) after confirming the user id exists; request-time verification stays DB-free (signature + expiry only). `SECRET_KEY` must be ≥32 bytes; rotating it invalidates all tokens (the only revoke). Protect an endpoint with `@authenticated` (`app/api/auth.py`) — sets `request.state.user_id`; a temporary bridge until an AuthMiddleware.
- **AppMode**: one `Application` serves both entrypoints. APP starts the HTTP client + DB; CLI starts DB only. Pass the mode to `setup_logging` and construct via `init_api_app()` / `get_cli_app()`.
- **Comments**: default to none. Add a concise one-liner only where intent isn't obvious from the code, stating *why*, never narrating *what*. Future work as `# TODO: <what>`.
- **Style**: Ruff + Mypy, line 120, double quotes, `X | None` (not `Optional`). Annotate every signature.

## Commands

Backend (from repo root, venv active):
```bash
pip install -r requirements.txt -r requirements.dev.txt
uvicorn app.main:app --reload          # run (http://127.0.0.1:8000, docs at /docs)
python -m ruff check app/ && python -m ruff format app/
python -m mypy app/
```

Admin CLI (`SECRET_KEY` must be set to issue tokens; generate one with `python -c "import secrets; print(secrets.token_urlsafe(32))"`):
```bash
python -m app.cli.main migrate                                             # alembic upgrade head
python -m app.cli.main user create --id alice --name "Alice"                # id is a chosen handle
python -m app.cli.main token alice                                          # verifies id exists, prints a JWT
python -m app.cli.main user list
```

Extension (from `extension/`):
```bash
npm install
npm run watch      # or: npm run compile
npm run package    # vsce package → .vsix
```
Press **F5** (Run Extension) from the `extension/` folder to launch an Extension Development Host.

## Git

Conventional Commits are enforced by `.githooks/commit-msg`; `.githooks/pre-commit` runs `make check`. Enable with `git config core.hooksPath .githooks`. (No Makefile yet — add one or adjust the hook before relying on pre-commit.)
