"""
SkillJar Agent — MCP server.

Thin registry that mounts tool groups onto a shared FastMCP instance.
Each tool group lives in tools/<domain>/tools.py and exposes a
register(mcp, get_client) function.

To add a new tool group:
  1. Create tools/<domain>/tools.py with a register() function
  2. Import and call it below
  3. That's it.

Only requires SKILLJAR_API_KEY — no Anthropic key needed.
The host agent (Claude Code, Cursor, etc.) handles all reasoning.

Run with:
  PYTHONPATH=src python mcp_server.py

Startup messages go to stderr so stdout stays clean for MCP stdio (Cursor, etc.).
"""

from mcp.server.fastmcp import FastMCP
from core.client import SkillJarClient

# ── Tool group imports ───────────────────────────────────────
from tools.curriculum.tools import register as register_curriculum
from tools.analytics.tools import register as register_analytics
from tools.enrollment.tools import register as register_enrollment
from tools.classroom.tools import register as register_classroom
from tools.content.tools import register as register_content


# ── Shared client (singleton, reused across all tool calls) ──
_client = None

def get_client() -> SkillJarClient:
    global _client
    if _client is None:
        _client = SkillJarClient()
    return _client


# ── MCP server ───────────────────────────────────────────────
mcp = FastMCP("skilljar-agent")

# Mount tool groups
register_curriculum(mcp, get_client)
register_analytics(mcp, get_client)
register_enrollment(mcp, get_client)
register_classroom(mcp, get_client)
register_content(mcp, get_client)


if __name__ == "__main__":
    import logging
    import os
    import sys

    # MCP SDK logs routine traffic (ListToolsRequest, etc.) at INFO on stderr.
    # Cursor's MCP panel labels *all* stderr as [error], which looks alarming.
    logging.getLogger("mcp").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    def _stderr(*args, **kwargs):
        print(*args, file=sys.stderr, flush=True, **kwargs)

    _stderr("=" * 50)
    _stderr("🚀 SkillJar Agent — MCP Server")
    _stderr("=" * 50)

    # Check for API key
    key = os.environ.get("SKILLJAR_API_KEY")
    if key:
        _stderr(f"🔑 SKILLJAR_API_KEY: ✅ (ends in ...{key[-4:]})")
    else:
        _stderr("🔑 SKILLJAR_API_KEY: ❌ not set")
        _stderr("   Set it with: export SKILLJAR_API_KEY=your-key")
        sys.exit(1)

    domain = os.environ.get("SKILLJAR_DOMAIN", "api.skilljar.com")
    _stderr(f"🌐 Domain: {domain}")

    # List registered tools
    _stderr("\n📦 Registered tool groups:")
    _stderr("   ├── curriculum  (search_courses, get_course_content, get_course_catalog)")
    _stderr("   ├── analytics   (get_enrollment_stats)")
    _stderr("   ├── enrollment  (lookup_user, enroll_user)")
    _stderr("   ├── classroom   (check_user_access)")
    _stderr(
        "   └── content     (create_course, update_course, create_lesson_from_html, "
        "create_lesson_from_file, batch_create_lessons, update_lesson_content)"
    )

    _stderr("\n✅ MCP server is running. Waiting for tool calls...")
    _stderr("   (stdio JSON-RPC on stdout; logs here on stderr. Ctrl+C to stop)")
    _stderr("=" * 50)

    import signal

    def _shutdown(sig, frame):
        import os
        os.write(2, b"\n\n\xf0\x9f\x9b\x91 MCP server stopped.\n")
        os._exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    mcp.run()