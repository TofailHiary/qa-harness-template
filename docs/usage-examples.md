# Usage examples

All examples use the fictional "Acme App" profile from `.claude/PROJECT-PROFILE.example.md`; ticket keys
are `APP-nnn`. Say the sentence in Claude Code with the project open.

## 1. Preflight, then a full run on a story

> "Run /env-health, then /full-qa APP-412 in full mode."

What happens: `env-health` probes the enabled capabilities (DB `SELECT 1`, API health, browser snapshot,
repos on the right branch, the change actually deployed, the release radar if Jira is on). `full-qa`
then runs Step 0 (`prompt-generator` writes the charter to `qa-evidence/APP-412-<date>/00-prompt-APP-412.md`),
Step 0a (six questions + Scope Lock), Phase 0 (`test-cases-generator` with a code-derived denominator),
Phases 1–7 (data, code review, DB, API, UI, security, perf), Phase 8 (verify bugs, assemble the
Execution Register and Evidence Ledger), Phase 8a (independent audit by `qa-verdict-auditor`), Phase 8b
(`qa-report`), and prints `GO / NO-GO / PARTIAL` with the confidence line and the escape classes checked.

## 2. One endpoint, quickly

> "/api-test GET /api/orders/:id — targeted mode, roles Manager and User, cross-tenant."

## 3. Is this a bug?

> "/bug-verifier — the order total on the dashboard shows 0 for account 1042 although the API returns 120."

Returns `CONFIRMED BUG / NOT A BUG / CANNOT CONFIRM / DUPLICATE` with the DB row, the API body and the
screen side by side; then `/bug-report` writes the report (and files it to the tracker only if §15 and the
user allow it).

## 4. After a bulk import

> "We imported 400 catalogue items yesterday. Run /latent-pattern-sweep on the catalogue pipeline, then /prod-sentinel."

## 5. Pair-testing in a shared browser

> "/test-together APP-431 — open the browser and tell me what to click."

Claude prepares a 6–10 case smoke sheet with live expected values (`scripts/api_peek.js` proves each
account), opens the browser, and guides one step per message, recording results with
`scripts/smoke_register.js`.

```bash
node .claude/skills/test-together/scripts/api_peek.js --base https://api.test.acme.example.com \
  --login-url https://api.test.acme.example.com/auth/login \
  --login-body '{"email":"manager1@acme.example.com","password":"${MANAGER_PASS}"}' --token-path data.token \
  --path api/orders --query "status=open&pageSize=10" --pick data.items --fields id,customer,total \
  --out qa-evidence/APP-431-20260101/smoke/expected-SM-01.json
```

## 6. Demo creator

A narrated, captioned MP4 of a real flow. First-time setup (per project):

```bash
node .claude/skills/demo-creator/scripts/setup.js          # installs Playwright, Chromium, edge-tts, ffmpeg; prints READY
```

Try the bundled offline sample (no accounts, no network, two browser contexts):

```bash
node .claude/skills/demo-creator/scripts/record.js --demo .claude/skills/demo-creator/templates --fast   # selector check
node .claude/skills/demo-creator/scripts/tts.js    --demo .claude/skills/demo-creator/templates --voice en-US-JennyNeural --rate -3%
node .claude/skills/demo-creator/scripts/record.js --demo .claude/skills/demo-creator/templates          # real recording (~1 min)
node .claude/skills/demo-creator/scripts/build_video.js --demo .claude/skills/demo-creator/templates --name "Notification settings.mp4"
node .claude/skills/demo-creator/scripts/frames.js --demo .claude/skills/demo-creator/templates --ids INTRO,P1-05,P1-07,OUTRO
```

Output: `templates/Notification settings.mp4` (1080p H.264 + AAC), `templates/out/chapters.json`,
`templates/out/frames/*.jpg` for the alignment check. For a real feature, in Claude Code:

> "/demo-creator — record a demo of the Notification settings page on https://test.acme.example.com with the Admin and User accounts from §7; the step list is docs/notification-settings-guide.md; voice en-US-AndrewNeural."

Claude writes `qa-evidence/<KEY>-<date>/demo/steps.json` + `flow.js` from the template, snapshots any row
the flow writes, runs the selector check, generates narration, records, builds, frame-checks, restores
the data and sends the MP4 (30 MiB attachment limit; a compact copy is made for longer videos).
Passwords are read by `flow.js` from the environment (`DEMO_PASS`), never written into the demo files.

## 7. Release sign-off

> "/release-check for the October release: APP-401, APP-412, APP-418 and APP-431."

## 8. Write the execution prompt for another session

> "/prompt-generator — prepare the full-qa prompt for PR #91 (bulk invite); a fresh session will run it; tell me whether /goal or /loop applies."

## 9. Explain a change to a non-engineer

> "/explainer PR #88 — what will a Manager see now that they could not before?"
