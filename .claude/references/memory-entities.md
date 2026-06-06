# Memory Entities (Reference)

> How QA findings are saved to auto-memory. Memory folder: `PROJECT-PROFILE.md` §12.

Each memory file is one fact with frontmatter (`name`, `description`, `metadata.type`). Types:
- **project** — ongoing work, goals, constraints, confirmed bugs (with severity + status).
- **feedback** — guidance the user gave on how to work (with the *why*).
- **reference** — pointers to external resources (tickets, dashboards, docs).
- **user** — who the user is (role, preferences).

Conventions:
- One fact per file; link related facts with `[[name]]`.
- Before creating a file, grep the memory folder for the affected endpoint / file / symptom and
  update the existing entry instead of duplicating.
- Keep the `MEMORY.md` index to one line per memory.

(No project-specific entities are pre-seeded — they accumulate as you run QA.)
