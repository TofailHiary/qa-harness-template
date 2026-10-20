# Known noise

Things that look like bugs during a pair-test but are not. Each row has the **source** that makes it
"expected": a tool's launch flags, a documented browser or framework behaviour, a code reference
(`path:line`), or a ticket key from the issue tracker (`PROJECT-PROFILE.md` §15). When you confirm a new
one, add a row with its source.

**An item without a source is a finding, not noise** (qa-standards → Judgement Discipline / Authoritative
Source Hierarchy). "It always does that" is not a source.

## Generic rows (apply to most web apps driven through Playwright MCP)

| What you see | Why | What to do | Source |
|---|---|---|---|
| Chrome bar: "You are using an unsupported command-line flag: --disable-blink-features=AutomationControlled" | Playwright starts Chrome with that flag | Close the bar | Playwright MCP launch flags |
| Chrome "Save password?" box after login | Browser feature | The user clicks Never | Browser behaviour (Chrome password manager) |
| Yellow or orange highlights on text | The user's Find bar (Ctrl+F) | Press Esc | Browser behaviour (Chrome find-in-page) |
| Login form already holds another email | Browser remembered it | `browser_type` replaces the value | Browser behaviour (Chrome autofill) |
| A toggle back to an earlier state fires no API call | A client-side query cache (e.g. React Query / TanStack Query, SWR) serves the cached response | Judge the case by the screen, not by the network tab | Framework behaviour (client query cache — confirm the cache config in the FE code and cite `path:line`) |
| Table rows read with an empty first cell | Data-grid tables often carry a row-indicator / selection column with no text | The card probe drops empty cells | Framework behaviour (data-grid component) |
| A tooltip read comes back empty | UI libraries open tooltips after an enter delay (e.g. MUI Tooltip `enterDelay`) | Hover, wait for a tooltip word (up to 4 s), then read | Framework behaviour (your UI library's tooltip delay) |
| Two rows with the same display name | Different records can share a name | Compare by the other columns or by the API's record id | Data shape (confirm the ids differ in the API or DB response) |

## Project-specific rows

Add this project's rows here with the same four columns. Typical sources: a Closed ticket (`APP-nnn`),
a code reference (e.g. `<frontend repo: PROJECT-PROFILE.md §3/§9>/src/.../AuthContext.tsx:66` — "the dev
build logs the token on purpose, gated on the env flag"), a fixture note (`PROJECT-PROFILE.md` §7/§13:
"account X has 3 console errors from deleted parents; the page survives them"), or a memory file
(`<memory folder: PROJECT-PROFILE.md §12>/project_<slug>.md`). No row without a source — and re-read a
ticket source live before relying on it, because a Closed ticket can be reopened.

| What you see | Why | What to do | Source |
|---|---|---|---|
|  |  |  |  |
