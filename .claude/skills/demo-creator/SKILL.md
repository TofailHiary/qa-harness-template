---
name: demo-creator
description: Use when the user wants a demo video, screen recording, narrated walkthrough or "ready demo" of an application feature or story (for a manager, a customer, a release note), wants an existing demo video redone with other steps, a shorter cut, another voice or another language, or asks which tool can turn a guide into a video. Not for live pair-testing (test-together) or for bug-evidence screenshots (evidence-manager).
argument-hint: "feature or story to demo, plus the guide/doc with the steps (optional: voice, language, pace)"
allowed-tools: ["Bash", "PowerShell", "Read", "Grep", "Glob", "mcp__filesystem__*", "mcp__mcp_server_mysql__mysql_query", "SendUserFile", "Skill(qa-standards)", "Skill(login)", "Skill(test-data-manager)"]
---

# Demo Creator: a narrated, captioned screen recording of a real application flow

> **Capability gate:** This skill requires **Demo** (`PROJECT-PROFILE.md §2`): Node 18+, Playwright
> with a Chromium build, ffmpeg on PATH, Python 3 with `edge-tts` (online neural voices) or an
> offline TTS engine. Before doing anything, run `node .claude/skills/demo-creator/scripts/setup.js --check`.
> If it prints `NOT READY`, tell the user which items are missing and offer to run `setup.js` without
> `--check` (it installs what it can); do not record until it prints `READY`. Browser (`§2`) is not
> needed — the recorder drives its own Playwright, not the MCP.

Produces one MP4 (1080p, H.264 + AAC) recorded live with Playwright: a caption bar and step label burned into every frame, an optional fixed top badge (for a disclaimer such as "custom test data"), a cursor that glides to each control, a highlight on the element being clicked, and a neural voice reading the same narration. Chapters, a timeline and a frame check come out with it. No video service and no paid API is involved: Playwright (`require('playwright')` resolves upward from this folder, so the project root needs `node_modules/playwright`), `edge-tts` (Python, Microsoft neural voices, free, needs internet) with an offline fallback (Windows SAPI, macOS `say`, Linux `espeak-ng`), and ffmpeg on PATH.

Follows `qa-standards` for data safety (the Mutation Safety Gate in `test-data-manager`: snapshot before, restore after, verify) and the Memory Ritual; takes logins from `login`. Defaults for voice, language, badge and demo folder come from `PROJECT-PROFILE.md §18`.

## ARGUMENTS

$ARGUMENTS

## If no arguments provided
Ask, then STOP until answered:
> "Which feature or story should the demo show, on which environment (URL from PROJECT-PROFILE.md §5), with which accounts (identifiers from §7)? Do you have a step list or guide, and do you want a specific voice, language or pace (§18 has the defaults)?"

## Install (one-time per project)

1. The skill folder holds 9 files: `SKILL.md`, `scripts/setup.js`, `scripts/record.js`, `scripts/tts.js`, `scripts/build_video.js`, `scripts/frames.js`, `templates/steps.example.json`, `templates/flow.example.js`, `templates/sample-app/index.html`. `python scripts/install.py --skill demo-creator --target <project>` (from the template repo) copies them; nothing in the scripts is project-specific.
2. Run **`node .claude/skills/demo-creator/scripts/setup.js`** from the project root. It installs whatever is missing and prints a check table: Playwright into the project's `node_modules` (creates `package.json` if there is none), the matching Chromium build (shared per machine in Playwright's browser cache), `edge-tts` for Python (`python -m pip install edge-tts`), ffmpeg (winget on Windows; a package-manager hint elsewhere), and it confirms the default neural voice is reachable plus which offline fallback voices exist. `--check` only reports. Needs Node 18+ and internet for the installs; Python 3 must already be installed. Ends with `READY` or `NOT READY: <items>`. Record the result in `PROJECT-PROFILE.md §2` (`Demo: on`).
3. Try the bundled offline sample: `node .claude/skills/demo-creator/scripts/record.js --demo .claude/skills/demo-creator/templates --fast` records the sample app in `templates/sample-app/` (no network, no accounts; the scripts fall back to `steps.example.json` / `flow.example.js` when a folder has no `steps.json` / `flow.js`). If that works, the pipeline works.

## Inputs

1. **A step list** — the guide or doc the user already has (a document, a `test-together` sheet, a story). Each step becomes one row of `steps.json`: `id`, `ctx` (which browser context: 1 = first account, 2 = second), `label` (shown bottom-right, e.g. "Part 1 · Admin · 7 of 26"), `text` (what the voice says AND the caption; one or two short sentences, numbers and screen words included; no passwords). Copy `templates/steps.example.json`.
2. **A flow** — `flow.js`, one `api.step(page, id, async () => {...})` per row, written with the Flow API below. Copy `templates/flow.example.js` (the sample-app demo, two accounts) and change the URL, the selectors and the ids. Keep the `login()` helper shape and the card helpers from the template.
3. **Accounts and data** that match the narration: read them live (API/DB) before writing `text`; a wrong number in the voice-over is worse than none. Identifiers from `PROJECT-PROFILE.md §7`; passwords from the env vars it names, read by `flow.js` at run time (`process.env.DEMO_ADMIN_PASS`), never typed into `steps.json`, `flow.js` or the chat.
4. **Optional `demo.json`** in the demo folder: `{"badge": "DEMO · TEST DATA"}` paints a fixed red badge at the top of every frame. Use it whenever the recording runs on production or on data the viewer must not mistake for real (default text in `§18`).

Demo folder (filesystem MCP writes are allowed there): `qa-evidence/<KEY>-<yyyymmdd>/demo/` (or any folder outside the product source) with `steps.json`, `flow.js`, optional `demo.json`, `snapshot-db-before-video.json`, optional `restore/` (a tiny second demo: `steps.json` + `flow.js` that puts the data back through the UI, run with `--fast`), and `out/` (tts, video, timeline.json, chapters.json, frames, run.log, the MP4).

## Workflow

1. **Scope and data.** Decide the parts, the accounts (one browser context per account), the records each step touches, and which steps WRITE data. List every row a save will change; snapshot those rows (ids, values, timestamps) into `snapshot-db-before-video.json` with the restore statements (or the restore flow) written out. Done when the narration numbers come from a read made today and the snapshot file exists.
2. **steps.json.** One row per step; the first row an intro card, the last an outro card. Done when `node .claude/skills/demo-creator/scripts/tts.js --demo <dir> --dry` prints every id with no gap.
3. **flow.js.** Build from the template. Every step waits for a visible result (`waitFor` on the exact text or heading the narration names) so the frame shows what the voice says. Done when the file loads (`node -e "require('<dir>/flow.js')"`).
4. **Selector check:** `node .claude/skills/demo-creator/scripts/record.js --demo <dir> --fast` (no narration waits; `--stop-after <id>` to stop early — on production stop at the last read-only step so no save is ever clicked by the check). Read `out/run.log`; fix every `STEP FAIL` and every `SLOW/CAUGHT` line (a 5 s timeout inside a step means a selector resolved to a vanished or doubled element). **Restore the data after every run that reached a save**, then verify the restore with a read. Done when all steps print `ok` in one run.
5. **Voice:** `node .claude/skills/demo-creator/scripts/tts.js --demo <dir> --voice <§18 voice> --rate -3%` (see Voices). After editing a few narrations, regenerate only those: `--only <ID>` (one id per call; loop it). Done when every `<id>.wav` is listed with a duration.
6. **Real recording:** read the pre-state of every row the flow writes (API or DB) right before, then start `node .claude/skills/demo-creator/scripts/record.js --demo <dir>` in the background as `(cd <project root> && nohup node … > <abs path>/out/run.log 2>&1 &)` — the parentheses matter: a bare `cd && nohup … &` backgrounds the cd too and the next command runs in the old folder. Poll the log (40 steps ≈ 7 min, 50 steps ≈ 11 min); never run two recordings at once. Done when the log ends with `videos …` and shows no `STEP FAIL` / `SLOW/CAUGHT`.
7. **Build:** `node .claude/skills/demo-creator/scripts/build_video.js --demo <dir> --name <Title>.mp4`, then `node .claude/skills/demo-creator/scripts/frames.js --demo <dir> --ids INTRO,<a few step ids>,OUTRO` and Read those frames: the caption on the frame must be the step named in `chapters.json` at that time (that is the audio/video alignment check; audio is placed on the same timeline). Done when the frames match and `ffprobe` shows h264 + aac at the expected duration.
8. **Restore and deliver.** Restore the snapshot rows and the switches touched by the flow (run `restore/` with `--fast` when the restore goes through the UI); verify with a read that matches the snapshot field for field. Send the MP4 with `SendUserFile` (display `attach`); its limit is **30 MiB**, so for a longer video send a compact copy (`ffmpeg -i master.mp4 -c:v libx264 -crf 23 -c:a aac -b:a 96k -movflags +faststart compact.mp4`) and keep the master. Give the full path, length, size and what is in it. Memory ritual: add the demo folder, voice, duration and any new selector lesson to the feature's memory file under `<memory folder: PROJECT-PROFILE.md §12>`.

## Flow API (what `flow.js` receives as `api`)

| Call | What it does |
| --- | --- |
| `api.ctx(n)` | The page of browser context n (created on first use, recorded at 1920×1080, overlay installed) |
| `api.step(page, id, fn)` | Sets caption + label from `steps.json`, runs `fn`, then waits until `max(voice + 1.3 s, 3 s)` so the voice finishes before the next step; records start/end for the timeline |
| `api.clickIt(page, locator, {scrollTop})` | Scrolls, glides the cursor, highlights, clicks; `scrollTop` first scrolls to the top (tabs and filters often sit under a fixed header) |
| `api.select(page, /^Grade/, 'Grade 6')` | ARIA select (MUI, Radix, headless-ui, native `role=combobox`): opens the combobox, picks the option by exact name (a regex is accepted too) |
| `api.flash(page, locator, ms)` | Cursor + highlight without a click, to point at a value the voice mentions |
| `api.expandSection(page, /^Show details/)` | Clicks an expand/collapse button only if its section is collapsed (`aria-expanded="false"` or absent) |
| `api.card(page, {title, subtitle, foot})` / `api.endCard(page, {...})` | Full-screen intro page / outro overlay |
| `api.sleep(ms)`, `api.FAST`, `api.heading(page, /re/)` | Utilities; `FAST` shortens every pause in the selector check |

The engine clears highlights page-wide (an element often disappears right after the click), gives every helper a 3–5 s timeout, logs the ones that fail as `SLOW/CAUGHT`, and writes `out/timeline.json` (wall-clock start/end per step, video start per context) that `build_video.js` turns into cuts, chapters and the narration track. The caption bar reserves its right end for the step label, so captions of up to four lines never collide with it.

## Voices

| Need | Voice | Notes |
| --- | --- | --- |
| English, default | `en-US-JennyNeural` (female) or `en-US-AndrewNeural` (male) | `edge-tts`; natural, fast; add `--rate -5%` for a calmer pace |
| English, newsreader style | `en-US-AriaNeural`, `en-US-GuyNeural` | |
| Other languages | e.g. `de-DE-KatjaNeural`, `es-ES-ElviraNeural`, `fr-FR-DeniseNeural`, `ar-SA-ZariyahNeural` | write `text` in that language; keep screen words in the UI's language inside quotes |
| Offline fallback | `--engine sapi` (Windows), `--engine say` (macOS), `--engine espeak` (Linux) | robotic; used automatically when edge-tts fails |

`python -m edge_tts --list-voices` shows all. One clip per step, normalised to 22050 Hz mono WAV; the build places each clip at its step's start on the final timeline.

## Rules that keep the recording honest and the run short

- One context per account. Logging in a second account in the same context replaces the first; if the app keeps its session in memory, a hard reload (`page.goto`) after login logs it out — navigate with clicks after login (verify per project).
- Reset every filter you changed before a step that depends on the full list (one filter back to "All" may leave another one set).
- Prefer role + exact name locators; append `.first()` to text locators that a live region duplicates.
- Paginated tables show N rows: a row past the Nth needs "Go to page 2" before its button, and "Back" may keep page 2 — click "Go to page 1" when it exists. A list that remembers its last filter/page gets it selected again before every later "View".
- Names from the database can carry a trailing space; write name regexes with `\s+` after the name and without `$`.
- A write step is proven by what the screen shows after it (toast, counter) — the narration states that text, and the step waits for it.
- Stop a stuck run by its PID (`out/run.log` prints it on the first line); killing every `node` process on the machine also kills every MCP server.
- Every run that saved data is followed by the restore + a verifying read before the next run.
- Keep passwords out of `text`, captions, `flow.js` and the chat; the login step reads them from the environment and types them unseen.
- On production: only a tenant the owner approved for demos, a badge disclaimer on every frame (`§18`), the selector check stopped before the first save, and a read-only pre-state + post-state read saved next to the demo.

## Deliverable

`<dir>/<Title>.mp4` plus `out/chapters.json` (id → seconds). Default length for a 40-step feature demo: 6–7 minutes; 50 steps with three accounts ≈ 11 minutes. A "highlights" cut is the same pipeline with a shorter `steps.json` and `flow.js`.

## Post-Session (MANDATORY)

- **Disproved memory:** when this run disproves an older memory fact, mark that entry `SUPERSEDED (<date>, <evidence id>)` and point it at the new one - never delete it silently.
Update auto-memory before claiming completion (qa-standards → Memory Ritual): the demo folder, voice, duration, the accounts used (identifiers only), the restore verification, and any selector lesson, in the feature's memory file under `<memory folder: PROJECT-PROFILE.md §12>`; one-line pointer in `MEMORY.md`; verify with `ls -la "<memory folder: PROJECT-PROFILE.md §12>/<file>.md"`. If memory cannot be persisted → HALT and tell the user.

