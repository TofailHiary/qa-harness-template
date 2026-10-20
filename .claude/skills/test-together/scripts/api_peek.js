#!/usr/bin/env node
'use strict';
// api_peek: authenticate with a pluggable method and print ONE GET response compactly. Read-only. Never prints the token.
//
//   node api_peek.js --base <https base URL> --path <endpoint/without/leading/slash> <auth> [options]
//
// Auth (exactly one):
//   --token-env NAME                      bearer token read from environment variable NAME
//   --login-url <url> --login-body '<json>' --token-path <dot.path>
//                                         POST the JSON to the login URL and take the token found at <dot.path> of the
//                                         response. ${VAR} inside --login-body is expanded from the environment, so a
//                                         password never appears on the command line
//   --cookie-env NAME                     Cookie header read from environment variable NAME
//
// Options:
//   --query "a=1&b=2"                     query string (with or without the leading ?)
//   --pick dot.path                       value to print from the JSON body (default: "data" when the body has it, else the body)
//   --fields a,b,c                        columns to print when the picked value is an array (dot paths allowed)
//   --limit N                             rows to print for an array (default 50)
//   --header k=v                          extra request header, repeatable
//   --accept-version X                    sends an accept-version header (for APIs that version by header)
//   --identity-from-claims a,b,c          copy the named JWT claims into request headers of the same name (off by default)
//   --out <path>                          save {env, at, url, status, identity, pick, value} as JSON. Relative to the project
//                                         root; a bare file name lands in qa-evidence/. Paths outside the project root are refused
//   --env <label>                         free label for the environment under test, printed and saved (default: TEST)
//
// Exit codes: 0 = HTTP 200 | 1 = any other HTTP status | 2 = usage, login or transport error.
// Needs Node 18+ (global fetch). Write --path WITHOUT a leading slash: Git Bash rewrites "/x" into
// "<drive>:/.../Git/x" (the script also undoes that rewrite).
const fs = require('fs');
const path = require('path');

// <repo>/.claude/skills/test-together/scripts -> <repo>
const ROOT = path.resolve(__dirname, '..', '..', '..', '..');
const EVIDENCE_DIR = 'qa-evidence';
const IDENTITY_CLAIMS = ['email', 'sub', 'id', 'user_id', 'role', 'role_id', 'tenant_id', 'account_id', 'organization_id'];

function usage() {
  const src = fs.readFileSync(__filename, 'utf8').split('\n');
  const lines = [];
  for (const l of src.slice(2)) { if (!l.startsWith('//')) break; lines.push(l.replace(/^\/\/ ?/, '')); }
  console.error(lines.join('\n'));
}

function fail(msg) { console.error('ERR', msg); process.exit(2); }

function parseArgs(argv) {
  const a = { header: [] };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    if (!k.startsWith('--')) fail('unexpected argument: ' + k);
    const name = k.slice(2);
    const v = argv[i + 1];
    if (v === undefined) fail('--' + name + ' needs a value');
    i++;
    if (name === 'header') a.header.push(v); else a[name] = v;
  }
  return a;
}

function pick(obj, dotPath) {
  if (!dotPath) return obj;
  return dotPath.split('.').reduce((o, k) => (o == null ? o : o[k]), obj);
}

function cell(v) {
  if (Array.isArray(v)) return '[' + v.map(cell).join(', ') + ']';
  if (v && typeof v === 'object') return JSON.stringify(v);
  return String(v);
}

// Replace ${VAR} inside every string of a parsed JSON value with the environment variable VAR.
function expandEnvDeep(v) {
  if (typeof v === 'string') {
    return v.replace(/\$\{([A-Za-z_][A-Za-z0-9_]*)\}/g, (_, name) => {
      if (process.env[name] === undefined) fail('environment variable ' + name + ' is not set (referenced in --login-body)');
      return process.env[name];
    });
  }
  if (Array.isArray(v)) return v.map(expandEnvDeep);
  if (v && typeof v === 'object') return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, expandEnvDeep(x)]));
  return v;
}

function jwtClaims(token) {
  const parts = String(token).split('.');
  if (parts.length !== 3) return {};
  try { return JSON.parse(Buffer.from(parts[1], 'base64url').toString('utf8')) || {}; } catch (e) { return {}; }
}

function identityOf(claims) {
  const out = {};
  for (const c of IDENTITY_CLAIMS) if (claims[c] !== undefined && claims[c] !== null) out[c] = claims[c];
  return out;
}

async function authenticate(a) {
  const modes = ['token-env', 'login-url', 'cookie-env'].filter((m) => a[m]);
  if (modes.length !== 1) fail('choose exactly one auth method: --token-env NAME | --login-url <url> --login-body <json> --token-path <dot.path> | --cookie-env NAME');
  if (a['token-env']) {
    const t = process.env[a['token-env']];
    if (!t) fail('environment variable ' + a['token-env'] + ' is empty or not set');
    return { headers: { Authorization: 'Bearer ' + t }, claims: jwtClaims(t) };
  }
  if (a['cookie-env']) {
    const c = process.env[a['cookie-env']];
    if (!c) fail('environment variable ' + a['cookie-env'] + ' is empty or not set');
    return { headers: { Cookie: c }, claims: {} };
  }
  if (!a['login-body'] || !a['token-path']) fail('--login-url needs --login-body <json> and --token-path <dot.path>');
  let body;
  try { body = JSON.parse(a['login-body']); } catch (e) { fail('--login-body is not valid JSON'); }
  body = expandEnvDeep(body);
  let res, text;
  try {
    res = await fetch(a['login-url'], { method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: JSON.stringify(body) });
    text = await res.text();
  } catch (e) { fail('login request failed: ' + e.message); }
  let json = null; try { json = JSON.parse(text); } catch (e) { /* not JSON */ }
  const token = json && pick(json, a['token-path']);
  if (!res.ok || !token || typeof token !== 'string') {
    const reason = (json && ((json.error && (json.error.message || json.error)) || json.message)) || res.statusText || 'no token at --token-path';
    console.error('LOGIN FAILED', res.status, typeof reason === 'string' ? reason : JSON.stringify(reason));
    process.exit(2);
  }
  return { headers: { Authorization: 'Bearer ' + token }, claims: jwtClaims(token) };
}

function resolveOut(p) {
  const rel = p.replace(/\\/g, '/');
  const target = path.isAbsolute(rel) ? path.resolve(rel) : path.resolve(ROOT, rel.includes('/') ? rel : path.join(EVIDENCE_DIR, rel));
  const back = path.relative(ROOT, target);
  if (back.startsWith('..') || path.isAbsolute(back)) fail('--out must stay under the project root (the folder four levels above this script)');
  return target;
}

(async () => {
  const argv = process.argv.slice(2);
  if (argv.length === 0 || argv.includes('--help') || argv.includes('-h')) { usage(); process.exit(2); }
  const a = parseArgs(argv);
  if (!a.base || !/^https?:\/\//.test(a.base)) fail('--base <https base URL> is required');
  if (!a.path) fail('--path <endpoint> is required (write it without a leading slash)');
  const env = a.env || 'TEST';
  const base = a.base.replace(/\/+$/, '');
  const outFile = a.out ? resolveOut(a.out) : null; // validate before any request is sent

  const auth = await authenticate(a);

  let p = a.path.replace(/\\/g, '/');
  const msys = p.match(/^[A-Za-z]:\/(?:.*?\/)?Git(\/.*)$/); // Git Bash turned "/x" into "<drive>:/.../Git/x"
  if (msys) p = msys[1];
  if (!p.startsWith('/')) p = '/' + p;
  const url = base + p + (a.query ? '?' + a.query.replace(/^\?/, '') : '');

  const headers = Object.assign({ Accept: 'application/json' }, auth.headers);
  if (a['accept-version']) headers['accept-version'] = a['accept-version'];
  if (a['identity-from-claims']) {
    for (const c of a['identity-from-claims'].split(',').map((s) => s.trim()).filter(Boolean)) {
      if (auth.claims[c] === undefined) console.error('warning: claim "' + c + '" is not in the token; header not sent');
      else headers[c] = String(auth.claims[c]);
    }
  }
  for (const h of a.header) {
    const i = h.indexOf('=');
    if (i < 1) fail('--header expects k=v, got "' + h + '"');
    headers[h.slice(0, i).trim()] = h.slice(i + 1);
  }

  const identity = identityOf(auth.claims);
  const who = identity.email || identity.sub || identity.user_id || identity.id;
  const t0 = Date.now();
  let res, text;
  try { res = await fetch(url, { headers }); text = await res.text(); } catch (e) { fail('request failed: ' + e.message); }
  const ms = Date.now() - t0;
  let body = null; try { body = JSON.parse(text); } catch (e) { /* not JSON */ }

  console.log(env + ' ' + res.status + ' ' + ms + 'ms GET ' + url.slice(base.length) + (who !== undefined ? '  as ' + who + (identity.role !== undefined ? ' (role ' + identity.role + ')' : identity.role_id !== undefined ? ' (role_id ' + identity.role_id + ')' : '') : ''));
  if (!body) { console.log(text.slice(0, 1500)); process.exit(res.status === 200 ? 0 : 1); }

  const meta = (body && body.meta) || (body && body.data && body.data.meta);
  if (meta && typeof meta === 'object') console.log('meta:', JSON.stringify(meta).slice(0, 400));

  const defaultPick = body && typeof body === 'object' && !Array.isArray(body) && 'data' in body ? 'data' : '';
  const pickPath = a.pick !== undefined ? a.pick : defaultPick;
  const value = res.status === 200 ? pick(body, pickPath) : body;
  const fields = a.fields ? a.fields.split(',').map((s) => s.trim()).filter(Boolean) : null;
  const limit = a.limit ? Number(a.limit) : 50;
  if (Array.isArray(value)) {
    console.log('rows: ' + value.length + (value.length > limit ? ' (showing ' + limit + ')' : ''));
    value.slice(0, limit).forEach((row, i) => console.log((i + 1) + '. ' + (fields ? fields.map((f) => cell(pick(row, f))).join(' | ') : cell(row))));
  } else if (value && typeof value === 'object' && JSON.stringify(value).length > 1500) {
    // a big object: show its shape so the next call can --pick the part that matters
    console.log('object keys:', Object.entries(value).map(([k, v]) => k + (Array.isArray(v) ? '[' + v.length + ']' : v && typeof v === 'object' ? '{}' : '=' + JSON.stringify(v))).join('  '));
    const arr = Object.keys(value).find((k) => Array.isArray(value[k]));
    if (arr) console.log('hint: --pick ' + (pickPath ? pickPath + '.' : '') + arr + ' --fields <a,b,c>');
  } else {
    console.log(JSON.stringify(value, null, 1));
  }

  if (outFile) {
    const out = outFile;
    fs.mkdirSync(path.dirname(out), { recursive: true });
    fs.writeFileSync(out, JSON.stringify({ env, at: new Date().toISOString(), url, status: res.status, identity, pick: pickPath || '(body)', value }, null, 1));
    console.log('saved', path.relative(ROOT, out).replace(/\\/g, '/'));
  }
  process.exit(res.status === 200 ? 0 : 1);
})().catch((e) => { console.error('ERR', e.message); process.exit(2); });
