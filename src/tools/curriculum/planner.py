"""
LLM-powered curriculum planner.

Used by the standalone CLI only. When running as an MCP server,
the host agent handles reasoning — this module is not loaded.
"""

import json
from pathlib import Path
import anthropic
from tools.curriculum.models import CurriculumPlan

PROMPT_PATH = Path(__file__).parent.parent.parent.parent / "prompts" / "curriculum_plan.md"


def generate_plan(
    user_prompt: str,
    course_context: str,
    model: str = "claude-sonnet-4-20250514",
) -> CurriculumPlan:
    client = anthropic.Anthropic()
    system = PROMPT_PATH.read_text()

    user_message = f"""## User Request
{user_prompt}

## Existing Course Content
{course_context}

Respond with a JSON object matching the CurriculumPlan schema. No markdown fences."""

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    return CurriculumPlan(**json.loads(raw))
