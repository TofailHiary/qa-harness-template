#!/usr/bin/env node
'use strict';
// smoke_register: one row per pair-test case; prints the results table and the confidence line for the close-out.
//
//   node smoke_register.js <run-folder> add <CASE-ID> <PASS|FAIL|NA|NYV|BLOCKED> "<what proved it>" [evidence-path]
//   node smoke_register.js <run-folder> summary
//
// Rows go to <run-folder>/smoke/register.jsonl (append-only). The summary uses the LAST row per case, in first-seen order,
// so a re-check simply adds a new row. <run-folder> is relative to the project root (e.g. qa-evidence/APP-123-20260101).
const fs = require('fs');
const path = require('path');

// <repo>/.claude/skills/test-together/scripts -> <repo>
const ROOT = path.resolve(__dirname, '..', '..', '..', '..');
const NAMES = { PASS: 'PASS', FAIL: 'FAIL', NA: 'NOT APPLICABLE', NYV: 'NOT YET VERIFIED', BLOCKED: 'BLOCKED' };
const [runArg, cmd, id, result, proof, evidence] = process.argv.slice(2);
if (!runArg || !cmd) { console.error('usage: smoke_register.js <run-folder> add|summary ...'); process.exit(2); }
const file = path.join(path.resolve(ROOT, runArg), 'smoke', 'register.jsonl');

if (cmd === 'add') {
  const key = String(result || '').toUpperCase();
  if (!id || !NAMES[key] || !proof) { console.error('add needs <CASE-ID> <PASS|FAIL|NA|NYV|BLOCKED> "<what proved it>" [evidence]'); process.exit(2); }
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const row = { case: id, result: NAMES[key], proof, evidence: evidence || null, at: new Date().toISOString() };
  fs.appendFileSync(file, JSON.stringify(row) + '\n');
  console.log(`${row.result.padEnd(16)} ${id} | ${proof}`);
} else if (cmd === 'summary') {
  if (!fs.existsSync(file)) { console.error('no register yet at', path.relative(ROOT, file)); process.exit(1); }
  const rows = fs.readFileSync(file, 'utf8').trim().split('\n').map((l) => JSON.parse(l));
  const order = []; const last = new Map();
  for (const r of rows) { if (!last.has(r.case)) order.push(r.case); last.set(r.case, r); }
  const cell = (s) => String(s == null ? '' : s).replace(/\|/g, '/');
  console.log('| Case | Result | What proved it | Evidence |');
  console.log('|---|---|---|---|');
  for (const c of order) { const r = last.get(c); console.log(`| ${c} | ${r.result} | ${cell(r.proof)} | ${cell(r.evidence)} |`); }
  const count = {}; for (const c of order) { const k = last.get(c).result; count[k] = (count[k] || 0) + 1; }
  const verified = (count.PASS || 0) + (count.FAIL || 0);
  const inScope = order.length - (count['NOT APPLICABLE'] || 0);
  console.log('');
  console.log('Counts:', JSON.stringify(count));
  console.log(`Verified ${verified} of ${inScope} cases; BLOCKED ${count.BLOCKED || 0}; NOT YET VERIFIED ${count['NOT YET VERIFIED'] || 0}; Remaining Risk: <fill in>`);
} else {
  console.error('unknown command', cmd); process.exit(2);
}
