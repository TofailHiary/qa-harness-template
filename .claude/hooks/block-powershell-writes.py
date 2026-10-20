#!/usr/bin/env python3
"""PreToolUse PowerShell - READ-ONLY QA (portable).

Closes the PowerShell gap that would bypass block-bash-writes.py. Same policy source
(harness-config.json -> protected_repos / owned_repos), same shape:
  1. mutating git verbs and npm publish/version/ci are refused (unless the command runs inside an
     OWNED repo and names no protected repo);
  2. with a protected repo in reach (named in the command, or the real cwd / a Set-Location target
     inside one): write cmdlets and their aliases, redirection, .NET File/StreamWriter APIs,
     Invoke-WebRequest/-RestMethod with -OutFile, Tee-Object -FilePath, Start-Process with
     redirected output, Export-*, Compress/Expand-Archive and interpreter writes are refused.
Here-string BODIES (@'...'@ / @"..."@) are DATA: documentation text inside a literal that merely
mentions a git verb must not be read as a command, exactly like heredoc bodies in the Bash guard.
Converters (ConvertTo-Json etc.) produce strings, not files, and are exempt.
Fail-closed on malformed hook input.
"""
import json
import re
import sys
import harness_config as hc

CFG = hc.load()
SRC_DIRS = CFG.get("protected_repos", [])
OWNED_DIRS = CFG.get("owned_repos", [])


def _alt(names):
    if not names:
        return None
    return r"(?<![A-Za-z0-9_.-])(" + "|".join(re.escape(d) for d in names) + r")(?![A-Za-z0-9_-])"


SRC_PATTERN = _alt(SRC_DIRS)
OWNED_PATTERN = _alt(OWNED_DIRS)

MUTATING_GIT = ["commit", "push", "merge", "rebase", "cherry-pick", "am", "apply",
                "restore", "checkout", "switch", "add", "rm", "mv", "update-ref", "clean",
                "reset", "stash", "worktree", "notes"]
MUTATING_NPM = ["publish", "version", "ci"]


def _block(reason):
    sys.stdout.write(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(2)


def _read_command():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            _block("READ-ONLY QA: empty hook input for PowerShell. Blocked by default.")
        data = json.loads(raw)
    except Exception as e:
        _block("READ-ONLY QA: could not parse PowerShell hook input (%s). Blocked by default." % type(e).__name__)
        return ("", "")
    tool_input = data.get("tool_input", {}) or {}
    return (tool_input.get("command", "") or "", data.get("cwd") or "")


def strip_herestring_bodies(cmd):
    """Replace the BODY of every PowerShell here-string with a placeholder.

    The opening token is @' or @" at the end of a line and the closing token is '@ or "@ at the
    start of a line. The cmdlets around the literal (Set-Content, Out-File, ...) stay visible to
    the write checks; only the literal text is hidden."""
    out = re.sub(r"@'[ \t]*\r?\n.*?\r?\n'@", "@'<herestring>'@", cmd, flags=re.S)
    out = re.sub(r'@"[ \t]*\r?\n.*?\r?\n"@', '@"<herestring>"@', out, flags=re.S)
    return out


def _in_src(text):
    return bool(SRC_PATTERN and re.search(SRC_PATTERN, text, re.IGNORECASE))


def owned_context(cmd, cwd):
    if not OWNED_PATTERN:
        return False
    cmd_norm = cmd.replace(chr(92), "/")
    cwd_norm = (cwd or "").replace(chr(92), "/")
    if _in_src(cmd_norm) or _in_src(cwd_norm):
        return False
    if re.search(r"/" + OWNED_PATTERN + r"(?:/|$)", cwd_norm, re.IGNORECASE):
        return True
    if re.search(r"(?:^|[;|&])\s*(?:Set-Location|cd|Push-Location|pushd)\s+[^;|&]*/" + OWNED_PATTERN + r"(?:/|\s|$)", cmd_norm, re.IGNORECASE):
        return True
    if re.search(r"git\s+(?:-C|--git-dir=|--work-tree=)\s*[^\s]*/" + OWNED_PATTERN + r"(?:/|\s|$|\.git)", cmd_norm, re.IGNORECASE):
        return True
    return False


def check_git_mutations(cmd):
    for seg in re.split(r"(?:;|\n|\|\||&&)", cmd):
        for sub in MUTATING_GIT:
            pat = r"(?i)(?:^|[^A-Za-z.])git\s+(?:-[A-Za-z]\s+\S+\s+|--[A-Za-z-]+(?:=\S+)?\s+)*" + re.escape(sub) + r"(?![A-Za-z-])"
            if re.search(pat, seg):
                # listing forms stay allowed
                if sub == "stash" and re.search(r"git\s+stash\s+(list|show)\b", seg, re.I):
                    continue
                if sub == "worktree" and re.search(r"git\s+worktree\s+list\b", seg, re.I):
                    continue
                if sub == "notes" and re.search(r"git\s+notes\s+(list|show)\b", seg, re.I):
                    continue
                _block("READ-ONLY QA (PowerShell): git %s is blocked." % sub)
        if re.search(r"(?i)(?:^|[^A-Za-z])git\s+branch\s+(-D|-d|-m|-M|--delete|--move|[A-Za-z0-9_./-]+\s*$)", seg):
            if not re.search(r"(?i)git\s+branch\s+(-a|-r|-v|-vv|--list|--contains|--merged|--no-merged|--show-current|--format)", seg):
                _block("READ-ONLY QA (PowerShell): git branch create/delete/rename is blocked.")
        if re.search(r"(?i)(?:^|[^A-Za-z])git\s+tag\s+(-d|--delete|-a|[A-Za-z0-9_./-]+\s*$)", seg):
            if not re.search(r"(?i)git\s+tag\s+(-l|--list|--contains|--points-at|--format)", seg):
                _block("READ-ONLY QA (PowerShell): git tag create/delete is blocked.")


def check_npm_mutations(cmd):
    for sub in MUTATING_NPM:
        if re.search(r"(?i)(?:^|[^A-Za-z])npm\s+" + sub + r"(?:\s|$|['\";&|])", cmd):
            _block("READ-ONLY QA (PowerShell): npm %s is blocked." % sub)


PS_WRITE_CMDLETS = (
    "Set-Content", "Add-Content", "Out-File", "New-Item", "Remove-Item", "Move-Item",
    "Copy-Item", "Rename-Item", "Clear-Content", "Set-ItemProperty", "Tee-Object",
    "Export-Csv", "Export-Clixml", "Start-Process", "New-ItemProperty", "Set-Acl",
    "Compress-Archive", "Expand-Archive", "Invoke-WebRequest", "Invoke-RestMethod",
    # ALIASES - PowerShell resolves these to the cmdlets above
    "sc", "ni", "ri", "rm", "mv", "cp", "ac", "rni", "rd", "md", "del", "erase", "move", "copy", "rename",
    # .NET, which bypasses cmdlets entirely
    "[System.IO.File]::WriteAllText", "[System.IO.File]::WriteAllLines",
    "[System.IO.File]::WriteAllBytes", "[System.IO.File]::AppendAllText",
    "[IO.File]::WriteAllText", "[IO.File]::AppendAllText", "StreamWriter",
)
# Converters produce a string, never a file - exempt or they false-block.
PS_NOT_A_WRITE = ("ConvertTo-Json", "ConvertTo-Csv", "ConvertTo-Xml", "ConvertFrom-Json")
# Treat as a write ONLY when the destination flag is present.
PS_NEEDS_DEST = {"Invoke-WebRequest": "-outfile", "Invoke-RestMethod": "-outfile",
                 "Tee-Object": "-filepath", "Start-Process": "-redirectstandardoutput"}
PS_INTERP = r"(?:^|[^A-Za-z0-9_./-])(python[0-9.]*|node|perl|ruby|php)(?:\s|$)"
PS_INTERP_WRITE = r"(?:open\s*\([^)]*[\x22\x27][wax]|writeFileSync|appendFileSync|\.write\s*\(|WriteAllText)"


def check_source_repo_writes(cmd, cwd):
    """Blocks a write cmdlet, redirection, .NET write or interpreter write when a protected repo is
    in reach - named in the command, or because the REAL cwd (or a Set-Location target) is inside one."""
    if not SRC_PATTERN:
        return
    cmd_norm = cmd.replace(chr(92), "/")
    cwd_norm = (cwd or "").replace(chr(92), "/")
    in_src = _in_src(cwd_norm) or bool(
        re.search(r"(?:^|[;|&])\s*(Set-Location|cd|Push-Location|pushd)\s+[^;|&]*" + SRC_PATTERN, cmd_norm, re.IGNORECASE))
    names_src = _in_src(cmd_norm)
    if not (in_src or names_src):
        return
    low = cmd.lower()
    if any(x.lower() in low for x in PS_NOT_A_WRITE) and not any(
            w.lower() in low for w in ("set-content", "out-file", "add-content", "export-")):
        return                        # pure conversion, no destination
    for c in PS_WRITE_CMDLETS:
        if c in PS_NEEDS_DEST and PS_NEEDS_DEST[c] not in low:
            continue
        if c[0].isalpha():
            hit = bool(re.search(r"(?:^|[^A-Za-z0-9_-])" + re.escape(c) + r"(?![A-Za-z0-9_-])", cmd, re.IGNORECASE))
        else:
            hit = c.lower() in low    # .NET forms contain [ ] : - plain containment
        if hit:
            _block("READ-ONLY QA (PowerShell): %s with a protected repo in reach is blocked. "
                   "Write to the memory dir or qa-evidence instead." % c)
    if re.search(r">>?[^>]", cmd) and (in_src or re.search(r">[>]?\s*\"?[^|<>\"]*[/\\]" + SRC_PATTERN, cmd, re.IGNORECASE)):
        _block("READ-ONLY QA (PowerShell): output redirection into a protected repo is blocked.")
    if re.search(r"(?:\[System\.IO\.)?File(?:\]::|\.)+?(?:WriteAllText|WriteAllBytes|AppendAllText|"
                 r"AppendAllLines|Create|Copy|Delete|Move|Open)", cmd):
        _block("READ-ONLY QA (PowerShell): .NET File API write/delete/move with a protected repo in reach is blocked.")
    if re.search(r"(?:StreamWriter|BinaryWriter|TextWriter)", cmd):
        _block("READ-ONLY QA (PowerShell): .NET StreamWriter/BinaryWriter with a protected repo in reach is blocked.")
    if re.search(PS_INTERP, cmd_norm, re.IGNORECASE) and re.search(PS_INTERP_WRITE, cmd, re.IGNORECASE):
        _block("READ-ONLY QA (PowerShell): interpreter write with a protected repo in reach is blocked.")


def main():
    cmd, cwd = _read_command()
    if not cmd:
        sys.exit(0)
    scan = strip_herestring_bodies(cmd)   # literal bodies are DATA, not commands
    if not owned_context(scan, cwd):
        check_git_mutations(scan)
        check_npm_mutations(scan)
    check_source_repo_writes(scan, cwd)
    sys.exit(0)


if __name__ == "__main__":
    main()
