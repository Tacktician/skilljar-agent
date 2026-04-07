Using the SkillJar MCP tools.

⚠️ This uses a **write** tool. Do not call any write API until I explicitly confirm.

**Inputs (I will fill these in):**
- **course_id:** `YOUR_COURSE_ID`
- **lesson_title:** `YOUR_LESSON_TITLE`
- **file_path:** `/absolute/path/to/lesson.html`  
  (Path must exist on the **same machine that runs the MCP server**, typically your Mac.)

**Task:** After I confirm, call **`create_lesson_from_file`** with exactly:
- `course_id` = above course_id  
- `title` = above lesson_title  
- `file_path` = above file_path  

**Rules:**
- Do **not** edit or rewrite the HTML file unless I ask.
- The file must be **`.html` or `.htm`** (tool requirement).
- Return the tool’s JSON response as-is (`success`, `lesson_id`, or `error`).

If the path is wrong or the file is missing, report the error and stop without guessing a different path.
