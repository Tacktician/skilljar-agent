Using the SkillJar MCP tools.

⚠️ **Write operation.** Do not call **`batch_create_lessons`** until I explicitly confirm (e.g. yes / go ahead) after you show **`course_id`**, **manifest path**, **lesson count**, and a **per-row summary** (title + whether `file_path` or `html_content`). Ask me for anything missing. Do not invent `course_id` or paths. You may use read-only tools unless I ask you not to.

---

## Required: JSON manifest file

Content authors maintain a **single manifest file** on disk (on the **same machine that runs the MCP server**). The manifest format is documented in **[README.md](../README.md)** (“Batch lesson manifest”).

**My inputs:**

- **course_id:** `YOUR_COURSE_ID`
- **manifest_path:** `/absolute/path/to/lessons.json` — file whose contents are a **JSON array** of lesson objects (not wrapped in an outer object).

**What you should do:**

1. Read **`manifest_path`** from disk and parse it as JSON. It must be an **array** (`[ ... ]`).
2. Validate each element: **`title`** (string) and **exactly one of** **`file_path`** or **`html_content`** (see README). Report invalid rows before any write.
3. For each `file_path`, verify the file exists (after `Path(...).expanduser()`). If a path is missing, stop and do not guess a replacement.
4. Show me a compact table: index, title, source (`file_path` basename or `html_content` length).
5. After I confirm, call **`batch_create_lessons`** with:
   - `course_id` = my course_id  
   - `lessons_json` = the **raw UTF-8 text** of the manifest file (must be valid JSON when parsed — same array the tool expects).  
   Alternatively, re-serialize the parsed array with `json.dumps(...)` so formatting is normalized; both work if the result is equivalent.

**Do not** build the lesson list by globbing a folder without a manifest. The manifest is the source of truth for **order** and **titles**.

---

## After the tool runs

Return the tool JSON as-is (`total`, `succeeded`, `failed`, `results` with `lesson_id` or errors per row).
