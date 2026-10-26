# QA Standards - judgement material (sources, freshness, discipline)

Part of `qa-standards`. Moved out of SKILL.md to keep the always-loaded file small; the headings are unchanged, so a reference such as "qa-standards -> <heading>" still lands here via the pointer left in SKILL.md.

---

## Data resources — exhaust these before recording a coverage gap

See `test-data-manager` → "Data resources" and "INPUT-CLASS FIXTURE REGISTRY", and `PROJECT-PROFILE.md §6/§7/§13`. Before you EVER record a coverage gap, a missing fixture, or "no access", confirm the resource table there is exhausted. Prefer fixtures created through the platform itself (its own API or typed project tools, `§14`) over hand-written INSERTs; snapshot the returned ids for the restore. **A closed port or a stopped container is an OPERATIONAL blocker, not a structural one** — start it rather than record a false gap. Only record a gap when the resource cannot be started at all.

---

## Authoritative Source Hierarchy — what wins when sources disagree

"Is this a bug?" is only answerable against a source that is allowed to define correct. Rank them.
**Higher rank wins. NEVER assume the expected behaviour — name the source you are judging against.**

| # | Source | Notes |
|---|---|---|
| 1 | The ticket / story currently under test | Scope and intent |
| 2 | Acceptance criteria on that ticket | The contract |
| 3 | Clarifying comments from the dev or product owner on that ticket | Often overrides a stale AC — read the whole thread |
| 4 | Official spec / wiki page | Only if not contradicted above |
| 5 | Design (mockups / prototype) | Visual truth only; never functional truth |
| 6 | Related stories / linked bugs | Context, not licence to widen scope |
| 7 | Current implementation (code) | What it DOES, never what it SHOULD do |
| 8 | API / backend contract (collection, route handler, schema) | |
| 9 | Database + column comment semantics | Read the comment before judging any value |
| 10 | Previous evidence / auto-memory | Historical. See the next section |
| 11 | Current reproducible behaviour | Evidence of state, never of correctness |

**Conflict rule.** If two sources disagree, that is a finding in itself — **investigate and report the
conflict**. Do NOT silently pick the one that makes the verdict easier. If nothing ranked 1-6 defines
the behaviour, you are inventing a requirement: say so, and either ask or record it as an ambiguity.
A developer's reply ("keep as is") is a ruling only when the written requirement allows it; a
requirement visible to the user and still unmet stays FAIL until product changes the requirement.

---

## Fresh vs Historical Evidence

Auto-memory, past reports, old screenshots, prior tracker comments and earlier sessions are
**supporting context, not proof of current correctness.** They are dated snapshots.

**Use them to:** understand context, recover commands and queries, locate the right area, reuse
fixtures and credentials, recall past defects, and avoid repeating discovery.

**NEVER use them to:** close a case, confirm a fix, or justify a PASS.

**Staleness is not selective — it applies to EVERY dated claim in the record, not just the one you
came for.** A memory file typically carries several: the code root cause, the ticket status, the
assignee, the fix version, the fixture credentials, the prevalence numbers, "table X is empty".
Re-checking one of them does NOT license trusting the rest. *(illustrative)* the gate was correctly
applied to the CODE in a record — catching that HEAD already held the fix — while the ticket status
in the SAME file was still read as "To Do" from three days earlier; the ticket had moved on, and a
pointless transition was recommended. Data-state memory ages fastest: code facts stay true, row
counts do not — before writing "secondary" / "out of scope" for any environment, run one `COUNT(*)`.

**The tracker rule is bidirectional.** The Completion Gate says *"a tracker status is NOT evidence"*
of a fix. The reverse is equally true: **a REMEMBERED status is not evidence that a ticket is still
open.** Before recommending ANY transition, or describing a ticket's state, re-read it live (the tracker
tool in `PROJECT-PROFILE.md §15`) — status, assignee, fix version, parent.

Anything entering a verdict MUST be re-executed in THIS run against the target environment.
If a recalled memory names a file, endpoint, table, column or flag — **verify it still exists**
before relying on it. When memory and today's evidence disagree, today's evidence wins, and the
memory file MUST be corrected in the post-session ritual (Supersession rule).

---

## Reuse assets, not conclusions

Reuse scripts, queries, saved requests, fixtures, logins, tokens and environments freely —
rebuilding them wastes the session. **Reusing a testing asset is not reusing its result.**
An old query is a tool; its old output is not evidence for today. A correction made to a result row
must also be patched INTO the script that produced it; a replayed row is never counted as fresh.

---

## Judgement Discipline

1. **Label the epistemic status when it changes the conclusion:** VERIFIED FACT (directly evidenced) · STRONG INFERENCE (evidenced, not proven) · HYPOTHESIS (needs investigation) · UNKNOWN. Never present an inference as a fact. *(illustrative: "code unchanged" was a fact; "therefore still broken" was an inference reported as a verdict and reversed the same day.)*
2. **Partially-empty beats empty.** `0`, `false`, `null`, `undefined`, `""`, `[]`, `{}`, missing key, no rows, Not Applicable, Loading, failed request, 401/403, Unknown are DIFFERENT states — verify what each means in THIS system. Empty pages are handled everywhere; **the row that EXISTS with one field absent or in a third state is where defects live.** Test the enum width: FE union vs API union.
3. **Not found ≠ not present.** Before writing BLOCKED / NOT APPLICABLE on a negative search, rule out: incomplete search scope · different naming · other environment · feature flag / conditional path · different fixture · timing · another code path.
4. **A shared component fixed ≠ every consumer fixed.** If the scope names several consumers, each is a register row: verified, or NOT YET VERIFIED — never "fixed everywhere because they share the code".
5. **Investigation scope ≠ change scope.** Read as widely as the root cause needs; report only inside the locked scope; never let the width of the reading silently widen the verdict.
6. **Coverage quality over count.** Priority: changed code → shared dependencies → calculations/aggregations → permission boundaries → prior regressions → edge states. One deeply verified critical path outranks twenty shallow checks — but mandatory scope is still every row.
7. **Test the fix against the real wire, never the mock.** A detector/parser/mapper is verified against the actual response body / file / event shape captured live in the target environment. *(illustrative: 65/65 unit tests passed against a string body; the backend sends a JSON envelope; the fix never fired.)*
8. **Recompute; do not transcribe.** API = UI proves transport. Correctness needs source records → expected calculation → API → UI, and the difference located.
9. **Current reality overrides memory.** A remembered PASS, FAIL, fixture, password, ticket status or table state is a lead to re-verify, never evidence. Staleness is not selective.
10. **Test the flow the product supports, not just a route that is reachable.** Before filing "X can never happen for user Y", find and execute the flow the product actually provides for Y (read the developers' own path); an API route production does not use carries NOT APPLICABLE, never a FAIL.
11. **Open the artifact in its real consumer.** A CSV/PDF/XLSX export is verified in Excel / a PDF viewer / the Office app, not by `Content-Type` and `content-length`; measure bytes with `arrayBuffer().byteLength`, not `text().length`.
12. **A host string in a bundle is not proof the page contacts it.** For any allow-list or "which hosts does X call" answer, confirm each host with the live CSP header and a real call site.

---

## Verdict Integrity - illustrative failure modes

- Two lanes independently filed the same bug for rows that were **correctly out of scope by design**
  (checked one type column without checking the other).
- A "user-facing" severity claim that was actually **latent** — the columns had no read path.
- A prevalence query returning **0 instead of 2** because it assumed `deleted_at` on a table that
  uses a `status` enum.
- "No prod access" recorded as a gap when a read-only prod path existed the whole time.
- A keyboard-focus bug filed from an accessibility scanner that the real Tab walk disproved.
