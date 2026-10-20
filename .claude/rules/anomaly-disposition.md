# Anomaly Disposition & Data-Release Gate (Always Loaded)

Why this exists: the most expensive production escapes are rarely coverage failures. In the typical
case the code was old and unchanged, the DATA changed, and — worst of all — the anomaly had already
been *observed* during QA and then dissolved: labelled "by design" and turned into a workaround, or
parked as "unresolved". This file makes both of those impossible.

---

## RULE 1 — An anomaly has exactly TWO legal dispositions

Anything surprising you observe — a merge you did not expect, an error you cannot explain, a value that
looks wrong, a path that behaves oddly — must end as **one** of:

1. **A filed ticket** (or an explicit finding in the run's verdict), or
2. **"Expected", WITH A CITED SOURCE** — quote it: acceptance criteria, a schema constraint, a code
   comment, a product decision with a name and date, or a written spec.

**These are NOT dispositions and must never close an anomaly:**

| Illegal disposition | What it looks like |
|---|---|
| "BY DESIGN" with no citation | a surprising merge/overwrite called intended, while the schema (a scalar FK = 1:1), the UI label (plural "Deploy item(s)") and per-row counters all contradict it |
| "Workaround adopted" | "do them one at a time when separate records are wanted" |
| "Unresolved without <tool/log/access>" | "cannot explain without the cloud logs" — never filed |
| "Known behaviour" / "it always did that" | age is not correctness |
| "Not related to this ticket" | file it separately; do not drop it |

**If you cannot cite a source, it is a BUG.** Filing a ticket later closed as working-as-intended costs
minutes. Not filing can cost weeks of silent production damage.

### The "by design" test — run it BEFORE you type those words
- Does the **schema** allow it? A scalar foreign key is 1:1 — it cannot represent N.
- Does the **UI** promise it? Plural labels, per-row counts, per-row status badges.
- Is there an **AC, code comment, or named product decision** that says so?
If all three are no, you invented the requirement. File the bug.

### Never write these phrases without an attached ticket id
"first-ever", "first time this path has been exercised", "genuine historical coverage gap",
"deterministic but unexplained", "masked error", "todo", "we route around it".
Each is a confession that something is unverified. Attach a ticket or the run is not finished.

---

## RULE 2 — A bulk data/content import IS a release. Gate it.

A content import changes **which code paths are reachable**. That is a deploy and gets a deploy's
scrutiny. Before any bulk import, answer in writing:

> **"What cardinality, mode, or format does this content introduce that production has never held?"**

Then **test that shape first**. Illustrative questions:

| Question | Typical answer before the import | What it would have caught |
|---|---|---|
| Will any (dimension A × dimension B) partition now hold **2+ records**? | 0 → hundreds | code that assumes "exactly one" per partition |
| Is mode `X` new **at scale**? | ~0 → hundreds | an `else` branch that never ran in production |
| Does this content introduce inputs with **an empty required field** (e.g. no text layer)? | yes | a parser that assumes the field is always populated |

**Post-import obligation:** re-test, on the newly imported content, every path the import makes reachable
end-to-end. "N/N rows imported clean" verifies the IMPORT; it says nothing about whether the records
behave downstream.

---

## RULE 3 — The three latent-defect patterns to hunt on every change

These stay invisible until the data grows into them. Grep for them in code you touch, then **check
production data to see whether the assumption still holds** (`Skill(latent-pattern-sweep)`).

| # | Pattern | Code smell | The data question |
|---|---|---|---|
| **P1** | **Cardinality** — "there is exactly one" | `const [first] = rows`, `rows[0]`, `.find()` used as *the* record, one INSERT from a SET | can this set now have **N > 1**? `GROUP BY <partition> HAVING COUNT(*) > 1` |
| **P2** | **Unexercised branch** — a mode the data never took | `if (type == "X") {...} else {...}` where one arm is rare | what is the **live distribution**? `GROUP BY <mode> COUNT(*)` |
| **P3** | **Input class** — "this field is always populated" | `a ?? b` on parser/OCR/upload output; `.required()` on a field some inputs cannot fill | which real inputs leave it **empty or whitespace**? |

**The check that catches all three: cross the code assumption against the PRODUCTION distribution.**
An assumption is not a bug until the data violates it — and it is not safe just because it has not yet.

---

## RULE 4 — A masked error is its own defect

If a real error is swallowed, overwritten, or reported as something else (a `throw` commented out
years ago so "no records found" surfaces as an unrelated `TypeError`), **file it separately**, even
after you have found the underlying bug. A masked error costs every future investigation, not just
this one.

---

## RULE 5 — Validation green is not feature green

A test that never reaches the network proved the **form**, not the **outcome**. Record the path each case
actually exercised (`Path exercised = validation-only | write`), and test the **write path** separately:

- a per-card `Save` on an existing record may mutate only local state → **no API call**
- the real write is often a later step (`Next` / `Assign` / bulk submit)
- **confirm with the network log AND a DB read-back**, never a success toast

Illustrative: five green cases all ran a path with zero API calls; the write path then exposed silent
content loss. The completion gate (check #11) flags a PASS that cites only a toast.
