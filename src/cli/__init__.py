"""
Standalone CLI for the SkillJar Agent.

Usage:
  skilljar-agent --test
  skilljar-agent "Refresh the PostAir Weather API course with Package Library content"
  skilljar-agent --new "Intro to API mocking with Postman"
  skilljar-agent --json "Extend the Git integration course"
"""

import argparse
import json
import os
import sys

from core.client import SkillJarClient
from tools.curriculum.resolver import resolve_courses
from tools.curriculum.scraper import scrape_course


def _run_test():
    """Test SkillJar API connection and basic functionality."""
    print("🔑 Checking SKILLJAR_API_KEY...", end=" ")
    key = os.environ.get("SKILLJAR_API_KEY")
    if not key:
        print("❌")
        print("   SKILLJAR_API_KEY is not set.")
        print("   Set it with: export SKILLJAR_API_KEY=your-key-here")
        sys.exit(1)
    print(f"✅ Found (ends in ...{key[-4:]})")

    print("🌐 Connecting to SkillJar API...", end=" ")
    try:
        client = SkillJarClient()
        courses = client.list_courses(bypass_cache=True)
    except Exception as e:
        print("❌")
        print(f"   {e}")
        sys.exit(1)
    print("✅ Connected")

    print(f"\n📚 Found {len(courses)} published courses:")
    for c in courses[:10]:
        print(f"   - {c.get('title', 'Untitled')} (id: {c['id']})")
    if len(courses) > 10:
        print(f"   ... and {len(courses) - 10} more")

    if courses:
        print("\n🔍 Testing fuzzy search...", end=" ")
        try:
            matches = resolve_courses(courses[0]["title"][:10], client, max_results=3)
            print(f"✅ Matched {len(matches)} courses")
            for m in matches:
                print(f"   - {m['match_score']} — {m.get('title', '')}")
        except Exception as e:
            print(f"⚠️  Search test failed: {e}")

    print("\n✅ All checks passed. You're good to go.")


def main():
    parser = argparse.ArgumentParser(description="SkillJar Agent")
    parser.add_argument("prompt", nargs="?", default=None, help="What you want to do (natural language)")
    parser.add_argument("--test", action="store_true", help="Test SkillJar API connection")
    parser.add_argument("--new", action="store_true", help="Skip course lookup; treat as new course request")
    parser.add_argument("--course-id", help="Skip fuzzy match; use this exact course ID")
    parser.add_argument("--model", default="claude-sonnet-4-20250514", help="Claude model to use")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output raw JSON")
    parser.add_argument("--clear-cache", action="store_true", help="Clear cached course listings before running")
    args = parser.parse_args()

    if args.test:
        _run_test()
        return

    if not args.prompt:
        parser.error("a prompt is required (or use --test to check your connection)")

    # Lazy import — only needed for plan generation, not --test
    from tools.curriculum.planner import generate_plan

    client = SkillJarClient()

    if args.clear_cache:
        client.clear_cache()
        print("🗑️  Cache cleared.")

    course_context = ""

    if not args.new:
        if args.course_id:
            print(f"📚 Fetching course {args.course_id}...")
            full_course = client.get_full_course_content(args.course_id)
            matches = [full_course]
        else:
            print(f"🔍 Searching for courses matching: '{args.prompt}'")
            matches = resolve_courses(args.prompt, client)

        if matches:
            best = matches[0]
            course_id = best["id"]
            print(f"✅ Best match: {best['title']} (score: {best.get('match_score', 'exact')})")

            if len(matches) > 1:
                print("   Other matches:")
                for m in matches[1:]:
                    print(f"   - {m['title']} ({m['match_score']})")

            print("📖 Scraping lesson content...")
            full_course = client.get_full_course_content(course_id)
            lessons = scrape_course(full_course)
            course_context = "\n\n---\n\n".join(l.summary() for l in lessons)
            print(f"   Found {len(lessons)} lessons")
        else:
            print("⚠️  No matching courses found. Treating as new course request.")
    else:
        print("🆕 New course mode — skipping course lookup.")

    print("🧠 Generating curriculum plan...")
    plan = generate_plan(args.prompt, course_context, model=args.model)

    if args.json_output:
        print(json.dumps(plan.model_dump(), indent=2))
    else:
        _print_plan(plan)


def _print_plan(plan):
    print(f"\n{'='*60}")
    print(f"📋 {plan.plan_type.upper()}: {plan.course_title}")
    print(f"{'='*60}")
    print(f"\n{plan.summary}\n")
    print(f"Audience: {plan.target_audience}")
    print(f"Prerequisites: {', '.join(plan.prerequisites) or 'None'}\n")

    print("── Learning Objectives ──")
    for i, obj in enumerate(plan.learning_objectives, 1):
        print(f"  {i}. [{obj.bloom_level}] {obj.description}")

    print("\n── Lesson Plan ──")
    total_min = 0
    for i, lesson in enumerate(plan.lesson_outlines, 1):
        total_min += lesson.estimated_minutes
        print(f"  {i}. {lesson.title} ({lesson.estimated_minutes} min, {lesson.content_type})")
        print(f"     Objective: {lesson.objective}")
        print(f"     Topics: {', '.join(lesson.key_topics)}")
    print(f"\n  Total estimated time: {total_min} minutes")

    if plan.research_todos:
        print("\n── Research TODOs ──")
        for todo in plan.research_todos:
            print(f"  [{todo.priority.upper()}] {todo.topic}")
            print(f"    → {todo.reason}")

    if plan.notes:
        print(f"\n── Notes ──\n  {plan.notes}")
    print()


if __name__ == "__main__":
    main()