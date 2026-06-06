/**
 * Memory Rotation Hook - SessionStart (portable).
 *
 * Operates on the auto-memory index at <memory_root>/MEMORY.md, where memory_root
 * comes from .claude/hooks/harness-config.json (written by /configure-project). If
 * that is empty, it is derived from CLAUDE_PROJECT_DIR the same way Claude Code
 * encodes project dirs (replace ':','/','\\' with '-', lowercase the drive letter).
 *
 * When MEMORY.md exceeds MAX_SIZE_KB, archives index entries older than KEEP_DAYS
 * into <memory_root>/archives/ and moves the matching per-topic .md files alongside.
 * Always exits 0 with a JSON {"additionalContext": "..."} on stdout.
 */
const fs = require('fs');
const path = require('path');
const os = require('os');

function encodeProject(p) {
  let e = p.replace(/[\\/:]/g, '-');
  if (e.length >= 2 && e[1] === '-') e = e[0].toLowerCase() + e.slice(1);
  return e;
}

function memoryDir() {
  // 1) explicit memory_root from harness-config.json
  try {
    const cfgPath = path.join(__dirname, 'harness-config.json');
    const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
    if (cfg.memory_root && cfg.memory_root.trim()) return cfg.memory_root;
  } catch (e) { /* fall through */ }
  // 2) derive from CLAUDE_PROJECT_DIR
  const root = process.env.CLAUDE_PROJECT_DIR || process.cwd();
  return path.join(os.homedir(), '.claude', 'projects', encodeProject(root), 'memory');
}

const MEMORY_DIR = memoryDir();
const MEMORY_FILE = path.join(MEMORY_DIR, 'MEMORY.md');
const ARCHIVE_DIR = path.join(MEMORY_DIR, 'archives');
const MAX_SIZE_KB = 24;
const KEEP_DAYS = 30;

const ENTRY_RE = /^- \[([^\]]+)\]\(([^)]+)\) — (.+)$/;
const DATE_RE = /(20\d{2}-\d{2}-\d{2})/;

function output(data) { console.log(JSON.stringify(data)); }

function run() {
  if (!fs.existsSync(MEMORY_FILE)) {
    output({ additionalContext: 'Memory: MEMORY.md not found — no rotation.' });
    return;
  }
  const stats = fs.statSync(MEMORY_FILE);
  const sizeKB = (stats.size / 1024).toFixed(1);
  if (stats.size <= MAX_SIZE_KB * 1024) {
    output({ additionalContext: 'Memory OK: ' + sizeKB + ' KB (threshold ' + MAX_SIZE_KB + ' KB). No rotation needed.' });
    return;
  }
  try {
    const content = fs.readFileSync(MEMORY_FILE, 'utf8');
    const lines = content.split('\n');
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - KEEP_DAYS);
    const cutoffStr = cutoff.toISOString().slice(0, 10);

    const keepLines = [], archiveEntries = [], archiveFiles = [];
    for (const line of lines) {
      const m = line.match(ENTRY_RE);
      if (!m) { keepLines.push(line); continue; }
      const filename = m[2];
      const dateMatch = (m[1] + ' ' + m[3]).match(DATE_RE);
      if (!dateMatch) { keepLines.push(line); continue; }
      if (dateMatch[1] >= cutoffStr) {
        keepLines.push(line);
      } else {
        archiveEntries.push(line);
        if (filename.indexOf('/') === -1 && filename.endsWith('.md')) archiveFiles.push(filename);
      }
    }
    if (archiveEntries.length === 0) {
      output({ additionalContext: 'Memory at ' + sizeKB + ' KB but all entries are within last ' + KEEP_DAYS + ' days. No rotation.' });
      return;
    }
    if (!fs.existsSync(ARCHIVE_DIR)) fs.mkdirSync(ARCHIVE_DIR, { recursive: true });
    const today = new Date().toISOString().slice(0, 10);
    const ts = today.replace(/-/g, '');
    const archiveIndexPath = path.join(ARCHIVE_DIR, 'MEMORY-archive-' + ts + '.md');
    const archiveBlock = '\n## Archived ' + today + ' (rotated when MEMORY.md was ' + sizeKB + ' KB)\n' + archiveEntries.join('\n') + '\n';
    if (fs.existsSync(archiveIndexPath)) fs.appendFileSync(archiveIndexPath, archiveBlock);
    else fs.writeFileSync(archiveIndexPath, '# Memory Archive\n' + archiveBlock);

    let moved = 0, missing = 0;
    for (const fname of archiveFiles) {
      const src = path.join(MEMORY_DIR, fname);
      const dst = path.join(ARCHIVE_DIR, fname);
      if (!fs.existsSync(src)) { missing++; continue; }
      try { fs.renameSync(src, dst); moved++; }
      catch (e) {
        try { fs.copyFileSync(src, dst); fs.unlinkSync(src); moved++; }
        catch (e2) { missing++; }
      }
    }
    const trimmed = keepLines.join('\n');
    const finalContent = content.endsWith('\n') ? (trimmed.endsWith('\n') ? trimmed : trimmed + '\n') : trimmed;
    fs.writeFileSync(MEMORY_FILE, finalContent);
    const newSize = (fs.statSync(MEMORY_FILE).size / 1024).toFixed(1);
    output({ additionalContext: 'MEMORY ROTATED: ' + sizeKB + ' KB -> ' + newSize + ' KB. Archived ' + archiveEntries.length + ' index entries + ' + moved + ' topic files to archives/MEMORY-archive-' + ts + '.md' + (missing ? ' (' + missing + ' missing)' : '') + '.' });
  } catch (err) {
    output({ additionalContext: 'Memory rotation failed: ' + err.message + '. Manual pruning recommended.' });
  }
}

run();
