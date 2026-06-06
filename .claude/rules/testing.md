# QA Testing Rules (Always Loaded)

## Investigation Flow
For EVERY task: Think deeply → Read code (trace FE→API→BE→DB) → Query DB → Test API → Validate in browser → Check regression → Document findings

## Cross-Layer Consistency (MANDATORY)
For each entity under test, verify data matches across DB → API → Browser:
1. Query DB directly via `mcp__mcp_server_mysql__mysql_query`
2. Call API via `mcp__http-client__*`
3. Check browser via `mcp__playwright__*`
4. Compare all three — on mismatch, document as bug

## Bug Classification (MANDATORY)
Every bug must classify as Frontend, Backend, Admin, or Both:
- API returns wrong data → check DB → if DB correct but API wrong → BE bug
- API returns correct data but UI shows wrong → FE bug
- No API call made when expected → FE bug
- API returns 500 → BE bug

## Evidence Rules
- Bug findings and reports appear in the chat conversation
- qa-evidence/ stores ONLY: API responses, screenshots, logs (prefixed with bug name)
- No index files or bug report markdown in qa-evidence

## Test Case Generation
Always generate test cases BEFORE testing using `/test-cases-generator` or Phase 0 of `/full-qa`

## Session Hygiene
Use `/clear` between unrelated QA tasks — stale test results degrade accuracy
