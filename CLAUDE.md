# CLAUDE.md — Project Context for AI Agents

This file provides full context for any AI agent (Claude Code, Cursor, etc.) picking up this project. Read this before making changes.

## What This Project Is

**SkillJar Agent** is a modular platform agent that connects to a SkillJar LMS instance via its REST API. It provides tools for curriculum planning, enrollment analytics, user management, and ILT (instructor-led training) classroom support.

It runs in two modes:
- **MCP server** — data-only tools consumed by a host agent (Claude Code, Cursor). The host agent does all reasoning. Only requires `SKILLJAR_API_KEY`.
- **Standalone CLI** — fetches data AND calls the Anthropic API to generate curriculum plans. Requires both `SKILLJAR_API_KEY` and `ANTHROPIC_API_KEY`.

The MCP server is the primary intended use case. The CLI exists for terminal-only workflows or CI/scripting.

## Project Structure

```
skilljar-agent/
├── mcp_server.py                # MCP registry — mounts all tool groups
├── pyproject.toml               # Package config, entrypoints, dependencies
├── .cursor/
│   └── mcp.json                 # Cursor MCP (python3, cwd, envFile, PYTHONPATH)
├── .env.example                 # Environment variable template → copy to .env
├── .gitignore
├── README.md                    # Project overview
├── QUICKSTART.md                # Setup guide (two tracks: IDE agent vs CLI)
├── CLAUDE.md                    # This file
├── docs/
│   └── skilljar-api.yaml        # Bundled SkillJar OpenAPI (reference)
├── prompts/
│   └── curriculum_plan.md       # System prompt for CLI planner (version-controlled)
└── src/
    ├── cli/
    │   ├── __init__.py          # Main CLI (argparse, --test, --new, --json, etc.)
    │   └── __main__.py          # python -m cli entrypoint
    ├── core/
    │   ├── __init__.py          # Convenience exports
    │   ├── cache.py             # File-based JSON cache with TTL
    │   ├── client.py            # SkillJar REST client (auth, pagination, caching)
    │   └── models.py            # Shared Pydantic models (CourseInfo, UserInfo, ToolResult)
    └── tools/
        ├── __init__.py
        ├── curriculum/
        │   ├── __init__.py
        │   ├── tools.py         # MCP tool definitions (search, scrape, catalog)
        │   ├── resolver.py      # Fuzzy title matching via SequenceMatcher
        │   ├── scraper.py       # HTML → structured lesson content
        │   ├── planner.py       # LLM-powered plan generation (CLI mode only)
        │   └── models.py        # CurriculumPlan, LessonOutline, etc.
        ├── analytics/
        │   ├── __init__.py
        │   └── tools.py         # get_enrollment_stats (starter implementation)
        ├── enrollment/
        │   ├── __init__.py
        │   └── tools.py         # lookup_user, enroll_user (⚠️ write ops)
        ├── content/
        │   ├── __init__.py
        │   └── tools.py         # create/update courses and lessons (⚠️ all write ops)
        └── classroom/
            ├── __init__.py
            └── tools.py         # check_user_access (ILT support, starter)
```

## Architecture Decisions

### Why MCP tools don't make nested LLM calls

When running inside Claude Code or Cursor, the host agent IS the LLM. Having the MCP server make its own Anthropic API call would be redundant — double the cost, double the latency, no benefit. The MCP server handles data retrieval AND mutations (course/lesson CRUD); the host agent reasons over results and decides what actions to take.

The `planner.py` module (which DOES call the Anthropic API) is only imported by the CLI, not the MCP server. It uses a lazy import so `--test` doesn't require an Anthropic key.

### Read vs write operations

Tool groups split into read-only (curriculum, analytics) and read-write (content, enrollment, classroom). All write tools have ⚠️ flags in their docstrings so the host agent knows to confirm with the user before executing. This is a convention enforced by tool descriptions, not by the server itself.

### Tool group registration pattern

Each tool group lives in `tools/<domain>/tools.py` and exposes a `register(mcp, get_client)` function. The MCP server calls each one to mount tools onto the shared FastMCP instance. Adding a new domain:

1. Create `src/tools/<domain>/tools.py` with a `register(mcp, get_client)` function
2. Add one import + one call in `mcp_server.py`
3. Done.

All tool groups share a singleton `SkillJarClient` via the `get_client` callable.

### Caching

`core/cache.py` implements a file-based JSON cache at `~/.cache/skilljar-agent/`. The `list_courses` and `list_paths` client methods use it (1 hour TTL by default). Configurable via `CACHE_TTL_SECONDS` env var. Set to `0` to disable.

The CLI has a `--clear-cache` flag. Programmatically: `client.clear_cache()`.

### Write operations require confirmation

Tools in `content/`, `enrollment/`, and `classroom/` that modify data have ⚠️ flags in their docstrings (e.g. `create_course`, `enroll_user`). This tells the host agent to confirm with the user before executing. This is a convention — the MCP server doesn't enforce it.

## Tool Group Status

| Domain | Status | Tools | Notes |
|---|---|---|---|
| curriculum | ✅ Implemented | `search_courses`, `get_course_content`, `get_course_catalog` | Read-only. `get_course_content` builds course description from `short_description` / `long_description_html` (and legacy `description` if present) |
| content | ✅ Implemented | `create_course`, `create_lesson_from_html`, `create_lesson_from_file`, `batch_create_lessons`, `update_lesson_content` | ⚠️ All write ops. Needs live testing. |
| analytics | 🔧 Starter | `get_enrollment_stats` | Read-only. Calls real API, needs testing against live data |
| enrollment | 🔧 Starter | `lookup_user`, `enroll_user` | `enroll_user` is a write op |
| classroom | 🔧 Starter | `check_user_access` | For ILT facilitators, needs `reset_password`, `provision_sandbox` |

### Planned tools (not yet implemented)

- `content`: `delete_lesson` (⚠️ destructive), `reorder_lessons`, `duplicate_course`, `publish_course` / `unpublish_course`
- `analytics`: `get_lesson_performance`, `get_assessment_results`, `get_path_progress`
- `enrollment`: `unenroll_user`, `batch_enroll`, `transfer_enrollment`
- `classroom`: `reset_user_password` (⚠️ write), `provision_sandbox` (⚠️ write), `get_live_session_roster`, `bulk_check_access`

## SkillJar API Details

- **Auth**: HTTP Basic — API key as username, empty password. Handled in `core/client.py`.
- **Base URL**: `https://api.skilljar.com/v1` (configurable via `SKILLJAR_DOMAIN` env var)
- **Pagination**: Cursor-based with `next` field. `client.get_all_pages()` handles this.
- **Docs**: https://api.skilljar.com/docs/

Key endpoints used (see also `docs/skilljar-api.yaml`):

| Endpoint | Method | Used by |
|---|---|---|
| `/v1/courses` | GET | curriculum (catalog, search) |
| `/v1/courses` | POST | content (`create_course` — uses `short_description`, `enforce_sequential_navigation`, `title`) |
| `/v1/courses/{id}` | GET | curriculum (course detail) |
| `/v1/courses/{id}` | PUT | content (`update_course`; maps `description` → `short_description` in the client) |
| `/v1/lessons` | GET | curriculum (`list_lessons` — requires `course_id` query param) |
| `/v1/lessons` | POST | content (`create_lesson` — `content_html`, `type`, `order`, `course_id`, `title`) |
| `/v1/lessons/{id}` | GET | curriculum (`get_lesson` — pass `course_id` query param) |
| `/v1/lessons/{id}` | PUT | content (`update_lesson`; maps legacy `body` → `content_html`) |
| `/v1/lessons/{id}/content-items` | GET | curriculum (always fetched per lesson; HTML merged into `scraping_html` when items exist — any lesson type) |
| `/v1/courses/{id}/lessons/order` | PUT | client only (`reorder_lessons` — not in bundled OpenAPI; may be legacy) |
| `/v1/courses/{id}/enrollments` | GET | analytics, classroom |
| `/v1/courses/{id}/enrollments` | POST | enrollment (enroll_user) |
| `/v1/users?email=` | GET | enrollment, classroom (user lookup) |
| `/v1/users/{id}` | GET | enrollment |
| `/v1/paths` | GET | curriculum (learning paths) |

## Environment Variables

| Variable | Required | Used by | Description |
|---|---|---|---|
| `SKILLJAR_API_KEY` | Always | All | SkillJar API key (dashboard → Settings → API Keys) |
| `ANTHROPIC_API_KEY` | CLI only | `planner.py` | Not needed for MCP server mode |
| `SKILLJAR_DOMAIN` | No | `client.py` | Default: `api.skilljar.com` |
| `CACHE_TTL_SECONDS` | No | `cache.py` | Default: `3600` (1 hour). Set `0` to disable. |

## Local Development

### Install

```bash
cd ~/Documents/skilljar-agent
pip install -e ".[cli]"    # includes Anthropic SDK for CLI mode
pip install -e .           # MCP server only, no Anthropic SDK
```

### Key commands

```bash
skilljar-agent --test                    # Verify SkillJar API connection
skilljar-agent --help                    # CLI usage
skilljar-agent --new "course idea"       # Generate plan for new course
skilljar-agent "update existing course"  # Fuzzy match + plan
PYTHONPATH=src python3 mcp_server.py     # Start MCP server locally (logs on stderr)
```

Non-`--test` CLI runs require **`SKILLJAR_API_KEY`** up front (clear error if missing). Course fetch and plan generation wrap SkillJar **`httpx`** errors and planner **`PlanGenerationError`** (Anthropic API, invalid JSON, or `CurriculumPlan` validation) with exit code 1.

### MCP config for Cursor (project)

See **[`.cursor/mcp.json`](.cursor/mcp.json)** — `python3 mcp_server.py` with **`cwd`**, **`envFile`** → `.env`, and **`PYTHONPATH=src`**. Copy **[`.env.example`](.env.example)** to `.env`; use `SKILLJAR_API_KEY=value` with **no spaces around `=`**. Startup diagnostics go to **stderr** so **stdout** stays clean for MCP stdio. Enable **skilljar-agent** under **Settings → MCP**; use **Agent** mode for tool calls.

### MCP config for Claude Code (`~/.claude/mcp.json`)

Set **`PYTHONPATH`** to `src` (or use `pip install -e .` so imports resolve without it):

```json
{
  "mcpServers": {
    "skilljar-agent": {
      "command": "python3",
      "args": ["/absolute/path/to/skilljar-agent/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/skilljar-agent/src",
        "SKILLJAR_API_KEY": "${SKILLJAR_API_KEY}"
      }
    }
  }
}
```

## Known Issues & Gotchas

### macOS / Linux PATH issue
`pip install -e .` may not put the `skilljar-agent` script on your PATH — scripts often land in `sysconfig`’s **scripts** directory (e.g. Python framework `bin/` on macOS), not only `$(python3 -m site --user-base)/bin`. Fix:
```bash
export PATH="$(python3 -m site --user-base)/bin:$(python3 -c 'import sysconfig; print(sysconfig.get_path("scripts"))'):$PATH"
```
Add that to `~/.zshrc` or `~/.bashrc`, then `source` it. Or use:
```bash
PYTHONPATH=src python3 -m cli
```
from the repo root. See [README.md](README.md) Installation and [QUICKSTART.md](QUICKSTART.md).

### PYTHONPATH for MCP server
Running `python3 mcp_server.py` directly may fail with `ModuleNotFoundError` because `core/` and `tools/` are inside `src/`. Either:
- Run with `PYTHONPATH=src python3 mcp_server.py`
- Or let the MCP config handle it (the installed package resolves paths correctly)

### FastMCP version compatibility
The installed `mcp` package may not support `FastMCP(description=...)`. The server uses `FastMCP("skilljar-agent")` with no description kwarg. Tool-level docstrings provide all the context the host agent needs.

### MCP stdio and logging
Do not print MCP startup banners to **stdout** — that corrupts JSON-RPC over stdio and breaks IDE clients (e.g. Cursor `Connection closed`). Use **stderr** for any human-readable logs before `mcp.run()`.

The MCP Python SDK also logs routine requests at **INFO** on stderr; **`mcp_server.py` sets the `mcp` and `httpx` loggers to WARNING** so Cursor’s MCP output is not flooded. Lines tagged `[error]` there are often **stderr text**, not application failures — check for `Successfully connected` / `connected: true`.

### SkillJar lesson HTML and modular lessons
The API returns lesson HTML in **`content_html`** (not `body`). `get_full_course_content()` sets a derived **`scraping_html`** field: top-level `content_html` / `description_html` (and legacy `body` if present), **plus** HTML aggregated from **`GET /v1/lessons/{id}/content-items`** for every lesson (paginated `results[]`, each item’s `content_html` / `header` / `order`; **`QUIZ`** / **`ASSET`** blocks without HTML get short placeholder text so previews are not falsely empty). If the aggregated items are already contained in the top-level HTML (normalized), the merge is skipped to avoid duplicates.

The **`scraper.py`** parser reads `scraping_html` first, then falls back to `content_html` / `body`. It emits **plain-text previews** for MCP/CLI: normal HTML text, headings, and code blocks; **document order** is preserved when prose and embeds alternate. **`<style>`** and **`<script>`** bodies are skipped so bundled lesson CSS/JS does not flood previews; **`<noscript>`** is **not** skipped (static fallback copy there is kept). **iframe** / **video** / **embed** / **object** tags add preview lines from the **`title`** attribute and **`src`**: Arcade (`*.arcade.software`) uses a line like **`Embedded Arcade: {title} — {url}`** (or URL-only if no title); other hosts use **`Embedded: {title}`** or a short host hint. Custom interactive widgets may still need parser extensions.

### Ctrl+C shutdown
The MCP server uses a `SIGINT` signal handler with `os._exit(0)` for clean shutdown. This prevents the async runtime traceback that otherwise spills on Ctrl+C. If you see traceback on shutdown, make sure you have the latest `mcp_server.py`.

## Roadmap Context

This started as a single-purpose curriculum planning tool (`skilljar-curriculum-agent`). It was refactored into a modular platform agent (`skilljar-agent`) to support a broader roadmap:

1. **Curriculum planning** (now) — search, scrape, plan courses
2. **Analytics** (next) — enrollment stats, completion rates, lesson performance
3. **Enrollment management** (next) — user lookup, enroll/unenroll, batch ops
4. **ILT classroom support** (future) — live workshop tools for facilitators: access checks, sandbox provisioning, password resets, roster management

The ILT use case is particularly important because it introduces **write operations** against SkillJar (password resets, enrollment changes). These need explicit user confirmation patterns in the host agent.

The eventual goal is for this to be usable by the full Customer Education team — not just developers — via Claude Code or similar agent IDEs.