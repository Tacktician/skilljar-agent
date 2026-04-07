# SkillJar Agent

A modular platform agent for SkillJar — curriculum planning, enrollment analytics, user management, and ILT classroom support. Runs as an MCP server from your IDE (Claude Code, Cursor) or as a standalone CLI.

## Tool Groups

| Domain | Status | Tools | Description |
|---|---|---|---|
| **Curriculum** | ✅ Implemented | `search_courses`, `get_course_content`, `get_course_catalog` | Fuzzy course matching, lesson scraping (incl. modular lessons via content-items), catalog browsing |
| **Content** | ✅ Implemented | `create_course`, `create_lesson_from_html`, `create_lesson_from_file`, `batch_create_lessons`, `update_lesson_content` | Course/lesson writes (⚠️ confirm before use) |
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

The MCP server provides data tools; your IDE's agent handles reasoning. See [QUICKSTART.md](QUICKSTART.md) for setup.

```json
{
  "mcpServers": {
    "skilljar-agent": {
      "command": "python",
      "args": ["/path/to/skilljar-agent/mcp_server.py"],
      "env": { "SKILLJAR_API_KEY": "your-key" }
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

## SkillJar API Reference

Auth: HTTP Basic — API key as username, empty password. Base URL: `https://api.skilljar.com/v1` (override with `SKILLJAR_DOMAIN`).

The client matches the [published API](https://api.skilljar.com/docs/) / `docs/skilljar-api.yaml`: lessons are under **`/v1/lessons`**, not nested under `/courses/.../lessons`.

| Endpoint | Purpose |
|---|---|
| `GET /v1/courses` | List courses (paginated) |
| `GET /v1/courses/{id}` | Course metadata (`short_description`, `long_description_html`, …) |
| `POST /v1/courses` | Create course (`short_description`, `title`, `enforce_sequential_navigation`, …) |
| `GET /v1/lessons?course_id={id}` | Lesson list for a course |
| `GET /v1/lessons/{lesson_id}?course_id={id}` | Lesson detail (`content_html`, `type`, …) |
| `GET /v1/lessons/{lesson_id}/content-items` | Blocks for modular / multi-part lessons |
| `POST /v1/lessons` | Create lesson (`content_html`, `type`, `order`, `course_id`, `title`) |
| `PUT /v1/lessons/{lesson_id}` | Update lesson |
| `GET /v1/courses/{id}/enrollments` | Enrollment list |
| `GET /v1/users?email=` | User lookup |
| `POST /v1/courses/{id}/enrollments` | Enroll a user |

Full docs: https://api.skilljar.com/docs/
