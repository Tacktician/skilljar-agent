# SkillJar Agent

A modular platform agent for SkillJar — curriculum planning, enrollment analytics, user management, and ILT classroom support. Runs as an MCP server from your IDE (Claude Code, Cursor) or as a standalone CLI.

## Tool Groups

| Domain | Status | Tools | Description |
|---|---|---|---|
| **Curriculum** | ✅ Implemented | `search_courses`, `get_course_content`, `get_course_catalog` | Fuzzy course matching, lesson scraping, catalog browsing |
| **Analytics** | 🔧 Starter | `get_enrollment_stats` | Enrollment counts, completion rates |
| **Enrollment** | 🔧 Starter | `lookup_user`, `enroll_user` | User lookup, course enrollment (write ops) |
| **Classroom** | 🔧 Starter | `check_user_access` | ILT support — access checks, sandbox troubleshooting |

Starter tools have working scaffolds against the SkillJar API. Extend them as your needs grow.

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

**Requires:** `SKILLJAR_API_KEY` + `ANTHROPIC_API_KEY`.

```bash
pip install -e ".[cli]"
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
├── tools/
│   ├── curriculum/              # Course planning tools
│   │   ├── tools.py             # MCP tool definitions
│   │   ├── resolver.py          # Fuzzy title matching
│   │   ├── scraper.py           # HTML → structured lesson content
│   │   ├── planner.py           # LLM planner (CLI mode only)
│   │   └── models.py            # CurriculumPlan schema
│   │
│   ├── analytics/               # Enrollment & performance analytics
│   │   └── tools.py
│   │
│   ├── enrollment/              # User enrollment management
│   │   └── tools.py
│   │
│   └── classroom/               # ILT classroom support
│       └── tools.py
│
└── cli.py                       # Standalone CLI entrypoint

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

Auth: HTTP Basic — API key as username, empty password.

| Endpoint | Purpose |
|---|---|
| `GET /v1/courses` | List published courses |
| `GET /v1/courses/{id}` | Course metadata |
| `GET /v1/courses/{id}/lessons` | Lesson list |
| `GET /v1/courses/{id}/lessons/{id}` | Full lesson with HTML body |
| `GET /v1/courses/{id}/enrollments` | Enrollment list |
| `GET /v1/users?email=` | User lookup |
| `POST /v1/courses/{id}/enrollments` | Enroll a user |

Full docs: https://api.skilljar.com/docs/
