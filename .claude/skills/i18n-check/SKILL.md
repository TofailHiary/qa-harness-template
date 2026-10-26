---
name: i18n-check
description: Use when a UI ships in more than one language or locale, supports right-to-left scripts, or a change touches translations, locale files, or date, number and currency formatting. Triggers include "check the translations", "test the Arabic or RTL layout", "is anything untranslated", "raw translation keys on the page", "check date and currency formats per locale", "does the German text fit".
argument-hint: "page(s) or flow, plus the locales to check (default: every locale the app ships)"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "mcp__playwright__*", "mcp__chrome-devtools__*", "mcp__mcp_server_mysql__mysql_query", "mcp__filesystem__write_file", "Skill(qa-standards)", "Skill(login)", "Skill(browser-test)", "Skill(visual-regression)", "Skill(bug-verifier)", "Skill(bug-report)", "Write"]
---

# i18n Check — every locale, rendered and measured

> **Capability gate:** This skill requires **Browser**. Before doing anything, read
> `PROJECT-PROFILE.md` §2 (Capability Map). If that capability is `off`, STOP and tell the user:
> "This project has no Browser configured, so `/i18n-check` is unavailable. Run
> `/configure-project` to enable it." Do not call this skill's tools when gated off.


Prove that each page reads correctly in each locale the app ships: no raw keys, no untranslated or half-filled
strings, layouts that survive longer text and right-to-left scripts, and dates, numbers and currencies formatted
the way the locale — or the product's own rule — says. Locale files give candidates; only the rendered page is
evidence.

Follows the shared standard — read `.claude/skills/qa-standards/SKILL.md` once per session. Verdict words come
from its **Verdict Contract**; expected formats come from its **Authoritative Source Hierarchy**: a product rule
("dates are always shown as 2026-10-26") outranks the locale default, so cite which one you used.
`Skill(browser-test)` owns the journeys and `Skill(visual-regression)` owns breakpoints and overflow
measurement; this skill adds the locale dimension to both. Register and ledger rows go into
`qa-evidence/<run-folder>/run.json` (qa-standards → `references/run-record.md`). Probe snippets:
[references/i18n-probes.md](references/i18n-probes.md).

## ARGUMENTS
$ARGUMENTS

## If no arguments provided
Ask, then STOP until answered:
> "Which pages or flow? Which locales (default: every locale the app ships)? Which roles? Test (default) or Dev?"

Do NOT switch locales or navigate until the Scope Lock is filled.

## Scope Lock (before any navigation)

| Field | Value |
|---|---|
| Pages / flows | |
| Locales | each one, with its direction (LTR / RTL) |
| Roles | `<roles: PROJECT-PROFILE.md §8>` — log in per `Skill(login)` |
| Locale switch | URL prefix / cookie / user setting stored in the DB / browser language |
| Locale files | `<locale files: PROJECT-PROFILE.md §9>` (Step 1 finds them when §9 is blank) |
| Breakpoints | default Desktop 1440 / Mobile 375 (`visual-regression`) |
| Environment | Test (default) — `PROJECT-PROFILE.md §5` |
| Branch / commit under test | `git rev-parse --short HEAD` in `<frontend repo: PROJECT-PROFILE.md §3/§9>` — stamps every ledger row |

`M` = pages × locales × the checks of Steps 3–5 that apply. Print it; every cell ends as a register row.

---

## Step 1 — Locale inventory

Use the i18n library and locale files named in `PROJECT-PROFILE.md §4/§9`. When they are blank, find them: Grep
the frontend for the library's set-up (i18next, FormatJS / react-intl, vue-i18n, ngx-translate or Angular i18n,
gettext `.po` files, a server-side `lang/` or `locales/` folder), and record what you found in §9 for the next run.

| Locale | Direction | Source file(s) | Keys | Fallback chain | Where the user's choice persists |
|---|---|---|---|---|---|

The fallback chain (`fr-CA` → `fr` → default) decides what a missing key shows. Where the choice persists
(cookie, local storage, a user-profile column — read it with `mcp__mcp_server_mysql__mysql_query`, the DB tool of
`PROJECT-PROFILE.md §6`) decides what the user sees after logout, on another device, and in e-mails.

## Step 2 — Static sweep of the locale files (leads, not findings)

Run the read-only key diff (probes §7; it prints and writes nothing) for the default locale against each other
locale:
- keys missing per locale;
- values identical to the default locale (untranslated — unless a brand name or a word the product keeps);
- placeholder mismatches (`{count}` in one locale and not in another: a runtime error or raw braces on screen);
- plural categories the locale needs but the file lacks (Arabic uses zero / one / two / few / many / other,
  Polish one / few / many / other — probes §6 prints the categories for any locale);
- markup inside strings.

A missing key may be dead: Grep its usage before it becomes a register row.

## Step 3 — Rendered sweep, page × locale

Switch the locale through the app's real mechanism (the switcher, the URL, the user setting) — never by editing
the DOM. On every page, with `mcp__playwright__browser_evaluate`:

1. **Raw keys and broken interpolation** (probes §1) — dotted keys such as `orders.empty_state.heading`,
   `{{name}}`, `{0}`, `%s`, "missing translation" markers, in text AND in `placeholder`, `title`, `aria-label`,
   `alt`. A hit is a lead: domain names, file names and version numbers match the pattern too — read each one.
2. **Untranslated text** (probes §2) — strings equal to the default-locale values from Step 2.
3. **`lang` and `dir`** (probes §4) — `<html lang>` equals the locale; `dir="rtl"` on RTL locales.
4. **Missing glyphs** — a screenshot per page × locale; boxes or question marks where letters belong are a
   font-coverage defect.
5. **Console and network** — the library's missing-key warnings (`mcp__playwright__browser_console_messages`) and
   a locale bundle that fails to load (`mcp__playwright__browser_network_requests`).

Screenshots take an explicit path: `filename: qa-evidence/<run-folder>/<id>-<page>-<locale>.png`.

## Step 4 — Layout under real text length and direction

- **Expansion.** German, Finnish and Russian text often runs 30–40 % longer than English. Run the overflow probe
  (§3) at each breakpoint with `Skill(visual-regression)`: truncation that cuts real content, buttons that wrap,
  labels that overlap and page-level horizontal scroll are FAIL candidates.
- **Simulated expansion** (probe §5) pads text in the page's DOM only, for a locale the app does not ship yet.
  Its hits are leads: confirm with a real locale before any FAIL (qa-standards → Judgement Discipline 7 — test
  against the real thing, not a stand-in). Reload the page afterwards.
- **Right-to-left.** The layout mirrors (navigation side, back and forward chevrons, progress direction, carousel
  order); alignment follows start / end, not left / right (probe §4 lists `text-align: left` inside an RTL page);
  left-to-right content inside RTL text stays isolated (phone numbers, e-mail addresses, codes, mixed product
  names); input carets and field alignment follow the direction.

## Step 5 — Formats and language rules

For each locale, compute the expected value with probe §6 (`Intl` in the same browser), unless the product states
its own rule — then cite that rule instead:
- dates (order, month names, 12 / 24 h, first day of the week in pickers) and which timezone is shown (the user's
  or the server's);
- numbers (decimal and grouping separators) and percentages;
- currencies (symbol, position, decimals per currency — some currencies have none);
- plurals at 0, 1, 2, 5, 11, 21 and 101 items;
- sorting — the order of accented and non-Latin names in sorted lists;
- input parsing — type `1,5` into a numeric field in a comma-decimal locale, save, and read the stored value
  back from the DB: 1.5, 15 or an error?

## Step 6 — Text rendered outside the page

API validation and error messages (sent with `Accept-Language`), e-mails, PDFs and exports, notifications and async
jobs (`PROJECT-PROFILE.md §11`) carry a locale too, and the saved preference must survive logout and login (DB
read-back of the user's locale column). Each in-scope consumer is a register row, or a named NOT YET VERIFIED.

## Output

| Page | Locale | Raw keys | Untranslated | Placeholders | Layout | RTL | Formats | Result |
|---|---|---|---|---|---|---|---|---|

- One register row per page × locale × check in `run.json`; screenshots and probe outputs are ledger rows with
  Env / commit / captured-at. Every row ends as **PASS / FAIL / BLOCKED / NOT APPLICABLE / NOT YET VERIFIED**
  (qa-standards → Verdict Contract); a FAIL cites the expected source (the locale file line, the product rule, or
  the `Intl` output for that locale).
- **Layer:** a missing or wrong string in the client bundle → FE; server-rendered text, API messages, e-mails and
  exports → BE; a wrong value stored after locale-specific input → Both until the read-back shows which side
  converted it.
- Every FAIL goes through `Skill(bug-verifier)`; confirmed ones go to `Skill(bug-report)`.
- Check the record before you state a result:
  `python .claude/skills/qa-standards/scripts/verdict_check.py qa-evidence/<run-folder>`.
  Called from an orchestrator, append to its `run.json` and leave the run verdict to the orchestrator.
- Name the escape classes you actively checked (qa-standards → Escape classes & their gates).

---

## Post-Session (MANDATORY — enforced)

Update auto-memory before claiming completion — full ritual in qa-standards -> Memory Ritual. If it cannot be persisted (hook/path/disk error) -> **HALT and tell the user**; never report success.

1. **Write/update** a memory file under `<memory folder: PROJECT-PROFILE.md §12>` with the `Write` tool (the only path it is allowed). Naming `project_<slug>.md` / `feedback_<slug>.md` / `reference_<slug>.md`; frontmatter `name` / `description` / `metadata.type`.
2. **Cross-reference first** — grep the folder for the page, the locale and the symptom; UPDATE an existing entry instead of filing a duplicate. A prior fact this run disproved (a locale list, a switch mechanism, a format rule) is marked **SUPERSEDED** with the date and the evidence id.
3. **Update** `MEMORY.md` with a one-line (<=200-char) pointer carrying the date in the title: `- [<title> YYYY-MM-DD](<file>.md) — <hook>`.
4. **Content:** pages × locales checked + date + Env + commit, the locale inventory (library, files, fallback chain, where the choice persists), the format rules the product states, verdict in Verdict Contract words, findings (ID, layer, NEW/DUPLICATE).
5. **Verify:** `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"` shows non-zero size, else HALT.
