# Bundled HTTP-Client MCP Server

A small, dependency-free MCP server that gives the QA harness direct HTTP testing
(`http_get`, `http_post`, `http_request`, `set_default_headers`). It is bundled so the
harness works out of the box without installing an external package.

- **Run:** `node server.js` (Node 18+). No `npm install` needed — it uses only Node built-ins.
- **Wired by:** `.mcp.json` (the `http-client` server entry), which `/configure-project` generates
  from `.mcp.json.template`, pointing at `${PROJECT_ROOT}/.claude/mcp-servers/http-client/server.js`.
- **Capability:** API (see `docs/capability-matrix.md`). If API is `off`, this server is dropped from
  the generated `.mcp.json`.

No credentials live here. Auth tokens are set per-request by the skills (e.g. a Bearer token from a
login flow) via `set_default_headers`.
