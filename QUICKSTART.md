# Quickstart Guide

Pick the track that matches your setup:

| Track | You have... | You need... | How it works |
|---|---|---|---|
| **A — IDE Agent** | Claude Code, Cursor, or similar | `SKILLJAR_API_KEY` only | MCP server provides SkillJar data; your IDE's agent does the reasoning |
| **B — Standalone CLI** | A terminal, no agent IDE | `SKILLJAR_API_KEY` + `ANTHROPIC_API_KEY` | CLI fetches data *and* calls Claude's API to generate plans |

Both tracks share steps 1–3. They diverge at step 4.

---

## 1. Install

```bash
git clone https://github.com/your-org/skilljar-agent.git
cd skilljar-agent

# IDE agent mode (no Anthropic SDK needed):
pip install -e .

# Standalone CLI mode (includes Anthropic SDK):
pip install -e ".[cli]"
```

Verify:

```bash
skilljar-agent --help
```

### If you get `command not found` (common on macOS / Linux)

`pip` installs the `skilljar-agent` script into a directory that depends on your Python build. **`$(python3 -m site --user-base)/bin` is not always that directory** (for example, the python.org macOS installer often puts scripts under the framework’s `bin/`, and the user-base `bin` may not even exist).

Add **both** the user-site `bin` and the active Python **scripts** path (from `sysconfig`) to your `PATH`. Put this in `~/.zshrc` (macOS default) or `~/.bashrc` (many Linux setups), then `source` the file or open a new terminal:

```bash
export PATH="$(python3 -m site --user-base)/bin:$(python3 -c 'import sysconfig; print(sysconfig.get_path("scripts"))'):$PATH"
```

You can confirm where the script landed:

```bash
python3 -c 'import sysconfig; print(sysconfig.get_path("scripts"))'
pip show -f skilljar-agent | grep -E 'bin/|scripts'
```

If you prefer not to edit `PATH`, use the alias workaround — reliable regardless of where pip puts scripts:

```bash
echo 'alias skilljar-agent="PYTHONPATH=/path/to/skilljar-agent/src python3 -m cli"' >> ~/.zshrc
source ~/.zshrc
```

Replace `/path/to/skilljar-agent` with the actual directory where you cloned the repo.

Either way, confirm it works:

```bash
skilljar-agent --help
```

---

## 2. Get Your SkillJar API Key

Both tracks need this.

1. Log into your SkillJar dashboard
2. Go to **Settings → API Keys** (requires admin permissions)
3. Copy the key

```bash
export SKILLJAR_API_KEY=your-key-here
```

Or use the env template:

```bash
cp .env.example .env
# Edit .env, then:
export $(grep -v '^#' .env | xargs)
```

---

## 3. Verify Your SkillJar Connection

```bash
skilljar-agent --test
```

This runs through each step and tells you exactly what's working or broken:

```
🔑 Checking SKILLJAR_API_KEY... ✅ Found (ends in ...a1b2)
🌐 Connecting to SkillJar API... ✅ Connected

📚 Found 12 published courses:
   - PostAir Weather API Fundamentals (id: abc123)
   - Advanced API Testing with Postman (id: def456)
   ...

🔍 Testing fuzzy search... ✅ Matched 3 courses

✅ All checks passed. You're good to go.
```

| Error | Cause | Fix |
|---|---|---|
| `SKILLJAR_API_KEY is not set` | Env var not loaded | `export SKILLJAR_API_KEY=your-key` or check `~/.zshrc` |
| `401 Unauthorized` | Bad or expired key | Regenerate in SkillJar dashboard |
| `Connection error` | Wrong domain | Set `SKILLJAR_DOMAIN` in `.env` |

---

## 4A. IDE Agent Setup (Claude Code / Cursor)

**Requirements:** `SKILLJAR_API_KEY` only. No Anthropic key.

### Test the MCP server starts

From the project root:

```bash
cd ~/Documents/skilljar-agent
PYTHONPATH=src python3 mcp_server.py
```

You should see (on **stderr**; stdout stays free for MCP JSON-RPC):

```
==================================================
🚀 SkillJar Agent — MCP Server
==================================================
🔑 SKILLJAR_API_KEY: ✅ (ends in ...a1b2)
🌐 Domain: api.skilljar.com

📦 Registered tool groups:
   ├── curriculum  (search_courses, get_course_content, get_course_catalog)
   ├── analytics   (get_enrollment_stats)
   ├── enrollment  (lookup_user, enroll_user)
   ├── classroom   (check_user_access)
   └── content     (create_course, create_lesson_from_html, create_lesson_from_file, batch_create_lessons, update_lesson_content)

✅ MCP server is running. Waiting for tool calls...
   (stdio JSON-RPC on stdout; logs here on stderr. Ctrl+C to stop)
==================================================
```

Press Ctrl+C to stop. You should see a clean shutdown:

```
🛑 MCP server stopped.
```

If you see `SKILLJAR_API_KEY: ❌ not set`, make sure the env var is exported in your current shell (check with `echo $SKILLJAR_API_KEY`).

### Configure Claude Code

Add to `~/.claude/mcp.json` (set **`PYTHONPATH`** to the repo’s `src` unless you use `pip install -e .`):

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

Restart Claude Code.

### Configure Cursor

This repo includes **[`.cursor/mcp.json`](.cursor/mcp.json)** (project-level): **`python3`** runs **`mcp_server.py`** with **`cwd`** and **`PYTHONPATH`** set to the repo, and **`envFile`** pointing at repo-root **`.env`** for `SKILLJAR_API_KEY`. If Cursor does not load `.env` into the MCP process, add **`"SKILLJAR_API_KEY": "${env:SKILLJAR_API_KEY}"`** under `env` and ensure the key is in the environment Cursor inherits, or check Cursor MCP logs.

Create **`.env`** from [`.env.example`](.env.example). Use **`SKILLJAR_API_KEY=...` with no spaces around `=`** (quotes around the value are optional for SkillJar keys; avoid smart quotes). Keep `.env` gitignored.

Cursor should pick up the config when the workspace is the repo root; enable **skilljar-agent** under **Settings → MCP**. See [Cursor MCP docs](https://cursor.com/docs/mcp). Use **Agent** mode in chat so tool calls are available.

### Available tools

All **five** tool groups are mounted automatically:

| Tool | Group | Description |
|---|---|---|
| `search_courses` | Curriculum | Fuzzy title match |
| `get_course_content` | Curriculum | Per-lesson plain-text previews from merged HTML (Arcade/embed lines, skips inline CSS/JS; see [CLAUDE.md](CLAUDE.md)) |
| `get_course_catalog` | Curriculum | Full course listing (cached) |
| `get_enrollment_stats` | Analytics | Enrollment count and completion rate |
| `lookup_user` | Enrollment | Find a user by email |
| `enroll_user` | Enrollment | Enroll a user in a course (⚠️ write) |
| `check_user_access` | Classroom | Check if a learner can access a course |
| `create_course` | Content | Create a course (⚠️ write) |
| `create_lesson_from_html` | Content | Create lesson from HTML (⚠️ write) |
| `create_lesson_from_file` | Content | Create lesson from file (⚠️ write) |
| `batch_create_lessons` | Content | Batch create lessons (⚠️ write) |
| `update_lesson_content` | Content | Update lesson body/title (⚠️ write) |

### Try it

Prompt your agent naturally:

```
"Search my SkillJar courses for anything about API testing, pull the
content for the best match, and propose a curriculum refresh with
new lessons on reusable test architecture."

"Check if user jane@example.com has access to the onboarding course."

"What's the completion rate for our Postman fundamentals course?"
```

The agent chains tools on its own — no second API key, no extra cost.

### How this differs from the CLI

The CLI bundles its own Claude API call via `planner.py` so it works without an agent IDE. In MCP mode, your IDE *is* the LLM. The MCP server does not call Anthropic; it exposes **read** tools (curriculum, analytics, etc.) and **write** tools (content, enrollment) for the host to use with confirmation.

---

## 4B. Standalone CLI Setup

**Requirements:** `SKILLJAR_API_KEY` + `ANTHROPIC_API_KEY`.

Use this from a plain terminal or for scripting/CI pipelines.

### Set your Anthropic key

```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Get one at [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys).

### Verify the Anthropic connection

```bash
python3 -c "
import anthropic
client = anthropic.Anthropic()
resp = client.messages.create(
    model='claude-sonnet-4-20250514',
    max_tokens=50,
    messages=[{'role': 'user', 'content': 'Say hello in exactly 5 words.'}]
)
print(f'Connected. Response: {resp.content[0].text}')
"
```

| Error | Cause | Fix |
|---|---|---|
| `authentication_error` | Bad Anthropic key | Check for trailing whitespace |
| `model_not_found` | Key lacks model access | Check your Anthropic plan |

### Run your first plan

```bash
# Fuzzy-match an existing course and propose a refresh
skilljar-agent "Refresh the PostAir Weather API course to cover Package Library"

# Target a specific course by ID
skilljar-agent --course-id abc123 "Add lessons on Collection Runner workflows"

# New course from scratch
skilljar-agent --new "Introduction to API Mocking with Postman Mock Servers"

# JSON output for piping into other tools
skilljar-agent --json "Extend the Git integration course with branch workflows"
```

---

## 5. Caching

Both tracks use the same file cache at `~/.cache/skilljar-agent/`. Course catalog results are cached for 1 hour by default.

```bash
# Check cache files
ls ~/.cache/skilljar-agent/

# Force a fresh pull
skilljar-agent --clear-cache "anything"

# Change TTL in .env
CACHE_TTL_SECONDS=1800   # 30 minutes
CACHE_TTL_SECONDS=0      # disable caching
```

---

## 6. Adding Your Own Tools

When you're ready to extend (e.g. sandbox provisioning, assessment results):

1. Create `src/tools/<domain>/tools.py` with a `register(mcp, get_client)` function
2. Add one import + one call in `mcp_server.py`
3. Restart your MCP server

See `src/tools/analytics/tools.py` for a minimal working example.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `command not found: skilljar-agent` | pip scripts dir not on PATH (common on macOS/Linux) | See install step 1 — add user-base `bin` **and** `$(python3 -c 'import sysconfig; print(sysconfig.get_path("scripts"))')` to PATH, or use the `python3 -m cli` / alias workaround |
| `KeyError: 'SKILLJAR_API_KEY'` | Env vars not loaded | Export them or use `python-dotenv` |
| `httpx.HTTPStatusError: 401` | Bad SkillJar key | Regenerate in SkillJar dashboard |
| `anthropic.AuthenticationError` | Bad Anthropic key (CLI only) | Check key at console.anthropic.com |
| `json.JSONDecodeError` / plan errors (CLI only) | LLM returned non-JSON or invalid schema | Retry; CLI surfaces **`PlanGenerationError`** with a short message. Check `prompts/curriculum_plan.md` |
| MCP tools not showing / `Connection closed` (Cursor) | Bad MCP config, missing key, or **stdout** polluted | Use [`.cursor/mcp.json`](.cursor/mcp.json) + `.env`; ensure `PYTHONPATH` includes `src`; server logs only to **stderr** before `mcp.run()`. Reload MCP in Settings |
| `401` from tools | SkillJar key missing in MCP process | Confirm `.env` has `SKILLJAR_API_KEY=...` (no spaces around `=`) and `envFile` path in `mcp.json` |
| Stale course results | Cache serving old data | Run with `--clear-cache` |
| No fuzzy matches found | Query too specific | Broaden query or lower threshold to `0.2` |
| `ModuleNotFoundError` | Package not installed | Re-run `pip install -e .` from the repo root |