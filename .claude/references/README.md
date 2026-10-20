# References

- `system-map.md` — the project's verified-from-code system map (TEMPLATE). `/configure-project`
  seeds it; every QA run verifies and extends one section; a section older than 60 days is treated as
  unverified. Skills that read it: `prompt-generator` (R5/R9), `pr-risk-analyzer`, `code-review`,
  `env-health`, `prod-sentinel`, `full-qa`.

Retired from the template (they were never referenced by a skill and drifted from the code): the old
`api-endpoints.md`, `database-queries.md`, `playwright-selectors.md`, `postman-collections.md` and
`memory-entities.md`. Their reusable content now lives where it is used: API surface and query shapes
in `system-map.md` sections 2 and 5 plus `db-check`; selector guidance in `browser-test` and
`test-together/references/page-probes.md`; Postman usage in `api-test`; memory conventions in
`CLAUDE.md` and `qa-standards` → Memory Ritual.
