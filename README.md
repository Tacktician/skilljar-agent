# SkillJar Agent

A modular platform agent for SkillJar — curriculum planning, enrollment analytics, user management, and ILT classroom support. Runs as an MCP server from your IDE (Claude Code, Cursor) or as a standalone CLI.

## Tool Groups

| Domain | Status | Tools | Description |
|---|---|---|---|
| **Curriculum** | ✅ Implemented | `search_courses`, `get_course_content`, `get_course_catalog` | Fuzzy course matching; lesson scraping merges **all** lessons with `content-items` when present (not only modular types), catalog browsing |
| **Content** | ✅ Implemented | `create_course`, `update_course`, `create_lesson_from_html`, `create_lesson_from_file`, `batch_create_lessons`, `update_lesson_content` | Course/lesson writes (⚠️ confirm before use) |
| **Analytics** | 🔧 Starter | `get_enrollment_stats` | Enrollment counts, completion rates |
| **Enrollment** | 🔧 Starter | `lookup_user`, `enroll_user` | User lookup, course enrollment (write ops) |
| **Classroom** | 🔧 Starter | `check_user_access` | ILT support — access checks, sandbox troubleshooting |

Starter tools have working scaffolds against the SkillJar API. Extend them as your needs grow.

## Installation (macOS / Linux)

From the repo root:

```bash
python3 -m pip install -e ".[cli]"   # CLI + Anthropic; use pip install -e . for MCP-only
```

After install, the `skilljar-agent` executable is placed in a **scripts directory** that depends on your Python install. On many Macs (e.g. python.org installer), that directory is **not** only `$(python3 -m site --user-base)/bin` — it is often the framework “scripts” path from `sysconfig`. If you see `command not found: skilljar-agent`, add **both** user-site `bin` and the active Python scripts path to `PATH` in `~/.zshrc` or `~/.bashrc`:

```bash
export PATH="$(python3 -m site --user-base)/bin:$(python3 -c 'import sysconfig; print(sysconfig.get_path("scripts"))'):$PATH"
```

Open a new terminal or run `source ~/.zshrc` (or `~/.bashrc`).

**Fallback** (no PATH change): from the repo directory,

```bash
PYTHONPATH=src python3 -m cli --help
```

More detail and troubleshooting: [QUICKSTART.md](QUICKSTART.md).

## Two Ways to Run

### IDE Agent Mode (Claude Code / Cursor)

**Requires:** `SKILLJAR_API_KEY` only. No Anthropic key.

The MCP server exposes SkillJar tools; the IDE agent does the reasoning.

- **Cursor (this repo):** [`.cursor/mcp.json`](.cursor/mcp.json) runs `python3` on `mcp_server.py` with `cwd` set to the repo, **`envFile`** set to `${workspaceFolder}/.env`, and `PYTHONPATH` → `src`. Copy [`.env.example`](.env.example) to `.env`. Enable **skilljar-agent** under Settings → MCP; use **Agent** chat for tool calls. Details: [QUICKSTART.md](QUICKSTART.md).

- **Claude Code / other hosts:** point `command`/`args` at `mcp_server.py` and ensure `PYTHONPATH` includes `src` (or use `pip install -e .`). Example:

```json
{
  "mcpServers": {
    "skilljar-agent": {
      "command": "python3",
      "args": ["/absolute/path/to/skilljar-agent/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/skilljar-agent/src",
        "SKILLJAR_API_KEY": "${env:SKILLJAR_API_KEY}"
      }
    }
  }
}
```

### Standalone CLI

**Requires:** `SKILLJAR_API_KEY` + `ANTHROPIC_API_KEY`. The CLI checks for `SKILLJAR_API_KEY` before calling SkillJar; planner failures (API, JSON, validation) exit with a clear message.

After installing with `pip install -e ".[cli]"` (see [Installation](#installation-macos--linux) if `skilljar-agent` is not on your `PATH`):

```bash
skilljar-agent "Refresh the PostAir Weather API course to cover Package Library"
skilljar-agent --new "Introduction to API Mocking with Postman Mock Servers"
skilljar-agent --json "Extend the Git integration course"
```

## Project Structure

```
src/
├── core/                        # Shared SDK layer
│   ├── client.py                # SkillJar REST client (auth, pagination, caching)
│   ├── cache.py                 # File-based JSON cache with TTL
│   └── models.py                # Shared Pydantic models
│
├── cli/                         # Standalone CLI (skilljar-agent entrypoint)
│   ├── __init__.py
│   └── __main__.py
│
├── tools/
│   ├── curriculum/              # Course planning tools
│   │   ├── tools.py             # MCP tool definitions
│   │   ├── resolver.py          # Fuzzy title matching
│   │   ├── scraper.py           # HTML → structured lesson content
│   │   ├── planner.py           # LLM planner (CLI mode only)
│   │   └── models.py            # CurriculumPlan schema
│   │
│   ├── content/                 # Course & lesson CRUD (write tools)
│   │   └── tools.py
│   │
│   ├── analytics/               # Enrollment & performance analytics
│   │   └── tools.py
│   │
│   ├── enrollment/              # User enrollment management
│   │   └── tools.py
│   │
│   └── classroom/               # ILT classroom support
│       └── tools.py

mcp_server.py                    # MCP registry — mounts all tool groups
.cursor/
└── mcp.json                     # Cursor MCP config (project-level)
.env.example                     # Template for SKILLJAR_API_KEY → copy to .env
docs/
└── skilljar-api.yaml            # Bundled OpenAPI reference (optional)
prompts/
└── curriculum_plan.md           # Version-controlled system prompt (CLI mode)
```

## Adding a New Tool Group

1. Create `src/tools/<domain>/tools.py`:

```python
import json

def register(mcp, get_client):
    @mcp.tool()
    def my_new_tool(param: str) -> str:
        """Tool description for the host agent."""
        client = get_client()
        # ... call client.get(), client.post(), etc.
        return json.dumps(result, indent=2)
```

2. Register it in `mcp_server.py`:

```python
from tools.my_domain.tools import register as register_my_domain
register_my_domain(mcp, get_client)
```

That's it. Restart your MCP server and the new tools are available.

## Batch lesson manifest (`batch_create_lessons`)

The MCP tool **`batch_create_lessons`** takes `course_id` and **`lessons_json`**: a string containing a **JSON array**. Content workflows can keep that array in a file (e.g. `lessons.json`) on the machine where the MCP server runs; your IDE agent reads the file and passes its contents as `lessons_json`.

### Format

- The file body must be a **JSON array** (`[ ... ]`), not an object wrapper.
- Each element is one lesson object:

| Field | Required | Description |
|--------|----------|-------------|
| `title` | Yes | Lesson title in SkillJar. |
| `file_path` | One of `file_path` **or** `html_content` | Path to a `.html` / `.htm` file. Expanded with `~`. Relative paths are resolved from the **MCP server process working directory** (often your repo root in Cursor); prefer **absolute paths** to avoid surprises. |
| `html_content` | One of `file_path` **or** `html_content` | Inline HTML body. Use for small snippets; large lessons should use `file_path`. |

Order in the array is the order lessons are created.

### Example `lessons.json`

```json
[
  {
    "title": "Chapter 1 — Introduction",
    "file_path": "/Users/you/projects/postair-lessons/01-intro.html"
  },
  {
    "title": "Chapter 2 — Workspace setup",
    "file_path": "/Users/you/projects/postair-lessons/02-workspace.html"
  },
  {
    "title": "Quick recap",
    "html_content": "<p>Review the key points from this module.</p>"
  }
]
```

### Prompt template

See [`prompts/batch_create_lessons.md`](prompts/batch_create_lessons.md) for copy-paste instructions to use with your IDE agent (confirm before write, validate manifest, then call the tool).

## SkillJar API Reference

Auth: HTTP Basic — API key as username, empty password. Base URL: `https://api.skilljar.com/v1` (override with `SKILLJAR_DOMAIN`).

The client matches the [published API](https://api.skilljar.com/docs/) / `docs/skilljar-api.yaml`: lessons are under **`/v1/lessons`**, not nested under `/courses/.../lessons`.

| Endpoint | Purpose |
|---|---|
| `GET /v1/courses` | List courses (paginated) |
| `GET /v1/courses/{id}` | Course metadata (`short_description`, `long_description_html`, …) |
| `POST /v1/courses` | Create course (`title`, `short_description`, optional `long_description_html`, `enforce_sequential_navigation`, …) |
| `GET /v1/lessons?course_id={id}` | Lesson list for a course |
| `GET /v1/lessons/{lesson_id}?course_id={id}` | Lesson detail (`content_html`, `type`, …) |
| `GET /v1/lessons/{lesson_id}/content-items` | Merged into lesson HTML for scraping (all lesson types when items exist) |
| `POST /v1/lessons` | Create lesson (`content_html`, `type`, `order`, `course_id`, `title`) |
| `PUT /v1/lessons/{lesson_id}` | Update lesson |
| `GET /v1/courses/{id}/enrollments` | Enrollment list |
| `GET /v1/users?email=` | User lookup |
| `POST /v1/courses/{id}/enrollments` | Enroll a user |

Full docs: https://api.skilljar.com/docs/
