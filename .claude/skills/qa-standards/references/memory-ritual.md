# QA Standards - Memory Ritual (full text)

Part of `qa-standards`. Moved out of SKILL.md to keep the always-loaded file small; the headings are unchanged, so a reference such as "qa-standards -> <heading>" still lands here via the pointer left in SKILL.md.

---

## Memory Ritual — MANDATORY post-session

**Every skill and sub-agent updates auto-memory before claiming completion.** Not optional. If memory cannot be persisted (hook/path/disk error) -> **HALT and tell the user**; never report success.

1. **Create/update a memory file** under `<memory folder: PROJECT-PROFILE.md §12>` (the ONLY path the `Write` tool is allowed — use `Write` directly here). Naming: `project_<slug>.md` (QA runs), `feedback_<slug>.md` (guidance), `reference_<slug>.md` (pointers). Frontmatter:
   ```markdown
   ---
   name: <short title>
   description: <one-line searchable hook>
   metadata:
     type: project | feedback | reference | user
   ---
   ```
2. **Cross-reference first.** Grep the memory folder for the endpoint / file path / user ID / symptom. If an entry already covers this root cause, **UPDATE it** with today's reproduction — do not file a duplicate.
   **Supersession rule:** when today's evidence DISPROVES a fact in an older memory, you must, in the SAME session, insert directly under that older file's frontmatter: `> ⚠️ SUPERSEDED on <date> by [[<new-file>]] — <what changed>` AND fix its `MEMORY.md` index line. A newer-dated file that repeats a disproven fact is the most dangerous record in the store — never leave the old claim unmarked.
3. **Update the index** `MEMORY.md` with one <=200-char line: `- [<title> YYYY-MM-DD](<file>.md) — <hook>`. The date in the link title is what the rotation hook uses to archive old entries (escape class E13).
4. **Required content:** feature/date, verdict = the canonical run verdict per *Verdict Contract* (**GO / NO-GO / PARTIAL**; a skill alias may follow in parentheses), bugs (ID, severity, layer, NEW/DUPLICATE), test data (IDs/accounts by identifier), root-cause location (`path:line`), regression risks for next time, any prior memory this run disproved.
5. **Verify:** `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` shows non-zero size, else HALT.
