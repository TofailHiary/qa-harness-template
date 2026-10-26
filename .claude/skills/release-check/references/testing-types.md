# Release Check - testing types

Part of `release-check`, moved out of SKILL.md to keep it small. Every type below is REQUIRED in a release run.

---

## Testing Types (ALL REQUIRED)

Smoke, Sanity, Regression, End-to-End, Positive, Negative, Edge Case, Full Cycle — all must pass for every area in scope. Cover every cell of the coverage matrix (roles, states incl. empty/single/many/null-vs-zero, inputs incl. negative/boundary, full flow, cross-tenant). Derive the denominator from the code (origin x mode x type x action), never by guessing (E12). Partially-empty beats empty: the row that exists with one field absent or in a third state is where defects live (Judgement Discipline #2).

**A release is always a regression -> `Skill(regression-runner)`** over the Step 0b indirect blast radius — actively re-test the shared components / endpoints / tables / async jobs / caches / downstream reports each change touches but is not "about". A shared component fixed is not every consumer fixed — each consumer in scope is its own register row (Judgement Discipline #4).
