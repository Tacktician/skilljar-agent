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
  python mcp_server.py
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
    import os
    import sys

    print("=" * 50)
    print("🚀 SkillJar Agent — MCP Server")
    print("=" * 50)

    # Check for API key
    key = os.environ.get("SKILLJAR_API_KEY")
    if key:
        print(f"🔑 SKILLJAR_API_KEY: ✅ (ends in ...{key[-4:]})")
    else:
        print("🔑 SKILLJAR_API_KEY: ❌ not set")
        print("   Set it with: export SKILLJAR_API_KEY=your-key")
        sys.exit(1)

    domain = os.environ.get("SKILLJAR_DOMAIN", "api.skilljar.com")
    print(f"🌐 Domain: {domain}")

    # List registered tools
    print(f"\n📦 Registered tool groups:")
    print(f"   ├── curriculum  (search_courses, get_course_content, get_course_catalog)")
    print(f"   ├── analytics   (get_enrollment_stats)")
    print(f"   ├── enrollment  (lookup_user, enroll_user)")
    print(f"   ├── classroom   (check_user_access)")
    print(f"   └── content     (create_course, create_lesson_from_html, create_lesson_from_file, batch_create_lessons, update_lesson_content)")

    print(f"\n✅ MCP server is running. Waiting for tool calls...")
    print(f"   (This will stay silent until an agent connects. Ctrl+C to stop)")
    print("=" * 50)

    import signal

    def _shutdown(sig, frame):
        import os
        os.write(2, b"\n\n\xf0\x9f\x9b\x91 MCP server stopped.\n")
        os._exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    mcp.run()