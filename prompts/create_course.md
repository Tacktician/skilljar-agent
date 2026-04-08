Using the SkillJar MCP tools.

⚠️ **Write operation.** Do not call **`create_course`** until I explicitly confirm (e.g. yes / go ahead) after you restate **title**, **short description**, and (if provided) **long description HTML**. Ask me for any missing values or placeholders. Do not invent values. You may use read-only tools (e.g. `get_course_catalog`) unless I ask you not to.

**Inputs (replace placeholders or supply when asked):**

- **title:** `YOUR_COURSE_TITLE`
- **description:** Short summary / catalog text (maps to SkillJar `short_description`)
- **long_description_html:** (optional) Full course description as HTML; omit or leave empty if none
- **enforce_sequential_navigation:** (optional) `true` or `false`; default false if omitted

**Task:** After I confirm, call **`create_course`** with those arguments (use empty string for optional long description if none).

Return the JSON as-is (`success`, `course_id`, `error`).

---

To **update** an existing course later, use **`update_course`** with `course_id` and only the fields that should change (`title`, `description`, `long_description_html`, `enforce_sequential_navigation`). Same confirmation rules apply for writes.
