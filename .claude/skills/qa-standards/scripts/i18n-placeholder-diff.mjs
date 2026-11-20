#!/usr/bin/env node
// i18n-placeholder-diff.mjs - read-only release / PR check for one class of silent UI bug: a shared text value GAINS an
// interpolation slot ({{word}}) for one screen, while other screens that read the same key never pass the word, so their
// users see the raw "{{word}}" (qa-standards -> Impact Analysis, "Shared text files").
// It lists every text key whose value GAINED a {{word}} between two git refs, finds the files that use each key at the new
// ref and reads how they call t() (i18next-style: t / i18n.t / $t):
//   MISSING VALUE   a caller calls t(key) with no values, with only a default string, or with an object that lacks the word
//                   -> the user sees the raw {{word}}                                                        (exit 1)
//   SUSPECT         callers found, call shape not recognised, and none of them changed in the range           (exit 1)
//   check by hand   values passed in a variable or a spread, a caller changed in the range, or a template-literal key
//                   whose static prefix fits (t(`a.b.${x}.${y}`)); open the page once                          (exit 3)
//   no caller found key built at run time; open the feature once                                              (exit 3)
//   passes values   every call passes an object literal that names each gained word (listed with --all)
// Usage:
//   node .claude/skills/qa-standards/scripts/i18n-placeholder-diff.mjs <from-ref> <to-ref> --repo <frontend repo>
//        --locale <locale file, path inside the repo> [--locale <another>] [--src <code dir in the repo, default src>]
//        [--root <dot.path inside the locale object>] [--all] [--eval-modules]
//   The locale files are <shared text files: PROJECT-PROFILE.md §9> (the default-language file is enough: a gained
//   word shows up there). Release: <from> = the last deployed commit, <to> = the release head (Impact Analysis item 0).
// Locale formats: .json (an object of strings, nested or flat), .js / .mjs / .cjs / .ts / .mts / .cts modules whose
// default export (or module.exports) is that object; a .ts module needs `typescript` installed in the repo. An i18next
// resource of the shape { translation: {...} } is unwrapped. The module must be self-contained (no imports); anything
// else -> exit 2 with the reason. A code module is EVALUATED (it runs code from the repo under test at that ref), so it
// needs --eval-modules: use it only on refs you trust; JSON never runs code. Placeholders are {{word}} (i18next / Handlebars style).
// Exit: 0 = nothing to fix or check, 1 = MISSING VALUE or SUSPECT, 3 = only keys to check by hand, 2 = usage or tool error.
// Read-only on the repo (git show / diff / grep); writes only to the OS temp folder (removed at the end).
import { execFileSync } from "child_process";
import { createRequire } from "module";
import fs from "fs";
import os from "os";
import path from "path";
import { pathToFileURL } from "url";

const USAGE =
  "usage: node i18n-placeholder-diff.mjs <from-ref> <to-ref> --repo <repo> --locale <file in repo> [--locale ...] [--src <dir>] [--root <dot.path>] [--all] [--eval-modules]";
let tmp = null;
const fail = (msg) => {
  console.error("i18n-placeholder-diff: " + msg);
  if (tmp) fs.rmSync(tmp, { recursive: true, force: true });
  process.exit(2);
};
const argv = process.argv.slice(2);
const opt = { locale: [], src: "src", all: false, evalModules: false };
const pos = [];
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a === "--all") opt.all = true;
  else if (a === "--eval-modules") opt.evalModules = true;
  else if (a === "--repo" || a === "--src" || a === "--root") opt[a.slice(2)] = argv[++i];
  else if (a === "--locale") opt.locale.push(argv[++i]);
  else if (a.startsWith("--")) fail(`unknown option ${a}\n${USAGE}`);
  else pos.push(a);
}
const [from, to] = pos;
if (!from || !to || !opt.repo || !opt.locale.length || opt.locale.some((l) => !l) || !opt.src) fail(USAGE);
const REPO = path.resolve(opt.repo);
if (!fs.existsSync(REPO)) fail(`repo not found: ${REPO}`);
const LOCALES = opt.locale.map((l) => l.replace(/\\/g, "/").replace(/^\.\//, ""));
const SRC = opt.src.replace(/\\/g, "/").replace(/^\.\//, "").replace(/\/$/, "");
const git = (...a) =>
  execFileSync("git", ["-C", REPO, ...a], { encoding: "utf8", maxBuffer: 64 * 1024 * 1024, stdio: ["ignore", "pipe", "pipe"] });
const require = createRequire(path.join(REPO, "package.json"));
let ts = null;
const typescript = () => {
  if (!ts) {
    try {
      ts = require("typescript");
    } catch (e) {
      fail(`a .ts locale needs typescript installed in ${REPO} (npm install there, or pass the JSON / JS locale)`);
    }
  }
  return ts;
};
tmp = fs.mkdtempSync(path.join(os.tmpdir(), "i18n-diff-"));
const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
let seq = 0;

const parseLocale = async (file, src, ref) => {
  const ext = path.extname(file).toLowerCase();
  if (ext === ".json") {
    try {
      return JSON.parse(src);
    } catch (e) {
      fail(`${file} at ${ref} is not valid JSON (${e.message})`);
    }
  }
  if (![".js", ".mjs", ".cjs", ".ts", ".mts", ".cts"].includes(ext))
    fail(`unsupported locale format ${ext || "(none)"} for ${file}: use .json or a self-contained .js / .mjs / .cjs / .ts module`);
  if (!opt.evalModules)
    fail(`${file} is a code module: reading it runs code from the repo under test at ${ref}. Pass --eval-modules only for a ref you trust, or point --locale at a JSON copy`);
  if (/^\s*import\s|\bimport\s*\(|\brequire\s*\(/m.test(src))
    fail(`${file} at ${ref} imports other files; pass a self-contained locale file (or its JSON)`);
  let code = src;
  const isTs = [".ts", ".mts", ".cts"].includes(ext);
  const cjs = ext === ".cjs" || ext === ".cts" || (!/\bexport\s+(default|const|\{)/.test(src) && /\bmodule\.exports\b|\bexports\.\w+\s*=/.test(src));
  if (isTs) {
    const t = typescript();
    code = t.transpileModule(src, {
      compilerOptions: { module: cjs ? t.ModuleKind.CommonJS : t.ModuleKind.ESNext, target: t.ScriptTarget.ES2020 },
    }).outputText;
  }
  const out = path.join(tmp, `locale-${++seq}${cjs ? ".cjs" : ".mjs"}`);
  fs.writeFileSync(out, code);
  try {
    if (cjs) return createRequire(out)(out);
    const mod = await import(pathToFileURL(out).href);
    return mod.default ?? mod;
  } catch (e) {
    fail(`cannot evaluate ${file} at ${ref}: ${String(e.message || e).split("\n")[0]}`);
  }
};

const load = async (ref) => {
  const flat = new Map();
  for (const file of LOCALES) {
    let src;
    try {
      src = git("show", `${ref}:${file}`);
    } catch {
      fail(`cannot read ${file} at ${ref} (unknown ref, or the path is not inside the repo?)`);
    }
    let root = await parseLocale(file, src, ref);
    if (root && typeof root === "object" && root.default && typeof root.default === "object" && Object.keys(root).length === 1) root = root.default;
    if (opt.root) for (const k of opt.root.split(".")) root = root && root[k];
    else if (root && typeof root.translation === "object" && root.translation) root = root.translation;
    if (!root || typeof root !== "object") fail(`${file} at ${ref}: no text object${opt.root ? ` at --root ${opt.root}` : ""}`);
    const walk = (node, keys) => {
      if (typeof node === "string") flat.set(keys.join("."), node);
      else if (node && typeof node === "object") for (const [k, v] of Object.entries(node)) walk(v, [...keys, k]);
    };
    walk(root, []);
  }
  if (!flat.size) fail(`parsed 0 text keys from ${LOCALES.join(", ")} at ${ref}`);
  return flat;
};
const words = (text) => new Set([...String(text).matchAll(/\{\{\s*([^{}\s,]+)[^{}]*\}\}/g)].map((m) => m[1]));
// i18next plural and context variants share the caller of the base key.
const baseKey = (k) => k.replace(/_(zero|one|two|few|many|other|custom)$/, "");

const before = await load(from);
const after = await load(to);
let changed;
try {
  changed = new Set(git("diff", "--name-only", `${from}..${to}`).split("\n").filter(Boolean));
} catch {
  fail(`git diff ${from}..${to} failed`);
}
// Search the code, never the locale files themselves or tests. A locale folder is excluded when it is not the code root.
const excludes = new Set([":!*.spec.*", ":!*.test.*"]);
for (const f of LOCALES) {
  const d = path.posix.dirname(f);
  excludes.add(d !== "." && d !== SRC ? `:!${d}` : `:!${f}`);
}
const sources = new Map();
const read = (f) => (sources.has(f) ? sources.get(f) : sources.set(f, git("show", `${to}:${f}`)).get(f));
const grep = (needle) => {
  try {
    return git("grep", "-n", "-F", needle, to, "--", SRC, ...excludes).split("\n").filter(Boolean);
  } catch {
    return []; // git grep exits 1 when nothing matches
  }
};
const fileOf = (line) => {
  const rest = line.slice(to.length + 1);
  return rest.slice(0, rest.indexOf(":"));
};
const grepFiles = (needle) => [...new Set(grep(needle).map(fileOf))];

// Every t(`<static prefix>${...` in the code, once: a key whose path starts with that prefix may be built by the call.
const templates = [];
for (const line of grep("t(`")) {
  for (const m of line.matchAll(/\bt\(\s*`([A-Za-z0-9_.]+)\$\{/g)) {
    if (m[1].includes(".") && m[1].length >= 3) templates.push({ prefix: m[1], file: fileOf(line) });
  }
}

// What the second argument of a call passes: "passes" (an object literal naming every gained word), "missing" (a
// default string, or an object without a gained word), "hand" (a variable, an expression or a spread).
const argKind = (src, idx, gained) => {
  const s = src.slice(idx, idx + 600).trimStart();
  if (/^["'`]/.test(s)) return "missing";
  if (!s.startsWith("{")) return "hand";
  let depth = 0;
  let end = s.length;
  for (let i = 0; i < s.length; i++) {
    if (s[i] === "{") depth++;
    else if (s[i] === "}" && --depth === 0) {
      end = i + 1;
      break;
    }
  }
  const obj = s.slice(0, end);
  if (obj.includes("...")) return "hand";
  return gained.every((w) => new RegExp(`\\b${esc(w)}\\b`).test(obj)) ? "passes" : "missing";
};

const judge = (key, gained) => {
  const full = baseKey(key);
  const segs = full.split(".");
  const last = segs[segs.length - 1];
  const parent = segs.slice(0, -1).join(".");
  const quoted = new RegExp(`["'\`]${esc(last)}["'\`]`);
  const files = [...new Set([...grepFiles(full), ...(parent ? grepFiles(`${parent}.`).filter((f) => quoted.test(read(f))) : [])])];
  const q = "[\"'`]";
  const missing = [new RegExp(`\\bt\\(\\s*${q}${esc(full)}${q}\\s*\\)`)]; // t("a.b.c")
  const passes = [new RegExp(`\\bt\\(\\s*${q}${esc(full)}${q}\\s*,`, "g")];
  if (parent) {
    missing.push(new RegExp(`\\bt\\(\\s*\`${esc(parent)}\\.\\$\\{[^}]+\\}\`\\s*\\)`)); // t(`a.b.${key}`)
    passes.push(new RegExp(`\\bt\\(\\s*\`${esc(parent)}\\.\\$\\{[^}]+\\}\`\\s*,`, "g"));
  }
  const kindOf = (f) => {
    const src = read(f);
    if (missing.some((re) => re.test(src))) return "missing";
    const kinds = [];
    for (const re of passes) for (const m of src.matchAll(re)) kinds.push(argKind(src, m.index + m[0].length, gained));
    if (kinds.includes("missing")) return "missing";
    if (kinds.length && kinds.every((k) => k === "passes")) return "passes";
    if (kinds.includes("hand")) return "hand";
    return "unknown";
  };
  const kinds = new Map(files.map((f) => [f, kindOf(f)]));
  const tpl = [...new Set(templates.filter((t) => full.startsWith(t.prefix) && t.prefix !== `${parent}.`).map((t) => t.file))]
    .filter((f) => !kinds.has(f));
  const of = (k) => files.filter((f) => kinds.get(f) === k);
  if (of("missing").length) return { status: "MISSING VALUE", files: of("missing") };
  if (!files.length && !tpl.length) return { status: "no caller found", files: [] };
  if (files.length && of("passes").length === files.length && !tpl.length) return { status: "passes values", files };
  if (of("hand").length || tpl.length || files.some((f) => changed.has(f)))
    return { status: "check by hand", files: [...of("hand"), ...of("unknown"), ...tpl] };
  return { status: "SUSPECT", files };
};

const rows = [];
for (const [key, text] of after) {
  const gained = [...words(text)].filter((w) => !words(before.get(key) ?? "").has(w));
  if (!gained.length) continue;
  rows.push({ key, gained, isNew: !before.has(key), ...judge(key, gained) });
}
const order = { "MISSING VALUE": 0, SUSPECT: 1, "check by hand": 2, "no caller found": 3, "passes values": 4 };
rows.sort((a, b) => order[a.status] - order[b.status]);
const count = (s) => rows.filter((r) => r.status === s).length;
console.log(
  `range ${from}..${to}: ${rows.length} key(s) gained a {{word}} | MISSING VALUE ${count("MISSING VALUE")} | SUSPECT ${count("SUSPECT")}` +
    ` | check by hand ${count("check by hand")} | no caller found ${count("no caller found")} | passes values ${count("passes values")}`,
);
for (const r of rows) {
  if (!opt.all && r.status !== "MISSING VALUE" && r.status !== "SUSPECT") continue;
  console.log(
    `${r.status.padEnd(15)} | ${r.key}${r.isNew ? " (new key)" : ""} | +{{${r.gained.join("}} {{")}}} | ${r.files.join(", ") || "-"}`,
  );
}
if (!opt.all) {
  // Keys to check by hand, one line per page file: open each file's page once.
  const groups = new Map();
  for (const r of rows) {
    if (r.status !== "check by hand" && r.status !== "no caller found") continue;
    for (const f of r.files.length ? r.files : ["(no caller found: key built at run time)"]) groups.set(f, [...(groups.get(f) || []), r.key]);
  }
  for (const [f, keys] of groups)
    console.log(`check by hand   | ${f} | ${keys.length} key(s): ${keys.slice(0, 3).join(", ")}${keys.length > 3 ? ", ..." : ""}`);
  if (groups.size || count("passes values")) console.log("(--all lists every key with its status)");
}
fs.rmSync(tmp, { recursive: true, force: true });
const bad = count("MISSING VALUE") + count("SUSPECT");
const look = count("check by hand") + count("no caller found");
process.exit(bad ? 1 : look ? 3 : 0);
