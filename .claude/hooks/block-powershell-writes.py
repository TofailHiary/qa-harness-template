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
Opaque execution is refused everywhere (-EncodedCommand, Invoke-Expression/iex of a computed string or
a pipeline, [scriptblock]::Create). The GUARD SURFACE (.claude/hooks/**, .claude/settings*.json) cannot be
written from PowerShell unless a human started the session with QA_HARNESS_ADMIN=1. Quoted text given
to a data-only cmdlet (Select-String, Write-Output, ...) is not read as a git command unless the line
also executes something.
Fail-closed on malformed hook input.
"""
import json
import os
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
ADMIN = os.environ.get("QA_HARNESS_ADMIN") == "1"


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
            pat = r"(?i)(?:^|[^A-Za-z.])git(?:\.exe)?\s+(?:-[A-Za-z]\s+\S+\s+|--[A-Za-z-]+(?:=\S+)?\s+)*" + re.escape(sub) + r"(?![A-Za-z-])"
            if re.search(pat, seg):
                # listing forms stay allowed
                if sub == "stash" and re.search(r"git\s+stash\s+(list|show)\b", seg, re.I):
                    continue
                if sub == "worktree" and re.search(r"git\s+worktree\s+list\b", seg, re.I):
                    continue
                if sub == "notes" and re.search(r"git\s+notes\s+(list|show)\b", seg, re.I):
                    continue
                _block("READ-ONLY QA (PowerShell): git %s is blocked." % sub)
        if re.search(r"(?i)\b(?:Start-Process|saps|start)\b[^;|\n]*\bgit(?:\.exe)?\b", seg):
            args = re.split(r"(?i)\bgit(?:\.exe)?\b", seg, 1)[-1]
            if any(re.search(r"(?i)(?<![A-Za-z-])" + re.escape(v) + r"(?![A-Za-z-])", args) for v in MUTATING_GIT):
                _block("READ-ONLY QA (PowerShell): Start-Process git with a mutating verb is blocked.")
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
PS_INTERP_WRITE = (r"(?:open\s*\([^)]*[\x22\x27][wax+]|\.write(?:_text|_bytes)?\s*\(|\.(?:unlink|rmdir|mkdir|touch|rename|symlink_to|hardlink_to)\s*\("
                   r"|os\.(?:remove|rename|renames|replace|unlink|rmdir|removedirs|makedirs|mkdir|truncate|chmod)"
                   r"|shutil\.(?:copy\w*|move|rmtree)"
                   r"|(?:writeFile|appendFile|rmSync|rmdirSync|unlinkSync|mkdirSync|renameSync|copyFileSync|cpSync|truncateSync|createWriteStream)\b"
                   r"|\b(?:fs|fsp|promises)\.(?:rm|rmdir|unlink|mkdir|rename|copyFile|cp|truncate|writeFile|appendFile)\s*\("
                   r"|File\.(?:write|delete|rename)|FileUtils\.|WriteAllText|WriteAllBytes)")


OPAQUE = [
    (r"(?i)\b(?:pwsh|powershell)(?:\.exe)?\b[^;|\n]*\s-(?:e|ec|en|enc|encodedcommand)\s+[A-Za-z0-9+/=]{8,}", "an encoded PowerShell command"),
    (r"(?i)\|\s*(?:iex|Invoke-Expression)\b", "a pipeline into Invoke-Expression"),
    (r"(?i)\[scriptblock\]::Create", "a script block built from a string"),
    (r"(?i)\bFromBase64String\b[^;\n]*(?:iex|Invoke-Expression|Invoke-Command|\.Invoke\()", "a decoded payload that is executed"),
]


def check_opaque(cmd):
    for pat, why in OPAQUE:
        if re.search(pat, cmd):
            _block("READ-ONLY QA (PowerShell): %s is blocked - the guard cannot inspect what would run." % why)
    for m in re.finditer(r"(?i)\b(?:Invoke-Expression|iex)\b\s*(?:-Command\s+)?([^;\n]*)", cmd):
        arg = m.group(1).strip()
        literal = re.fullmatch(r"\x27[^\x27]*\x27|\x22[^\x22$`]*\x22", arg)
        if not literal:
            _block("READ-ONLY QA (PowerShell): Invoke-Expression of a computed string is blocked - "
                   "the guard cannot inspect what would run. Run the command in plain text instead.")


_PS_DATA = {"select-string", "sls", "write-output", "write-host", "echo", "write-verbose", "write-information",
            "write-warning", "out-host"}
_PS_EXEC_HINT = re.compile(
    r"(?i)\b(?:Invoke-Expression|iex|Invoke-Command|icm|Start-Process|saps|Start-Job|powershell|pwsh)\b"
    r"|(?:^|[^&])&(?!&)|\[scriptblock\]|\.Invoke\(|\bcmd(?:\.exe)?\s+/c\b"
    r"|\|\s*(?:bash|sh|python[0-9.]*|node|perl|ruby)\b|(?:^|[;|\n]\s*)\.\s+\S")


def mask_inert_quotes(cmd):
    if _PS_EXEC_HINT.search(cmd):
        return cmd
    out = []
    for part in re.split(r"(&&|\|\||;|\||\n)", cmd):
        toks = part.strip().split()
        first = toks[0].lower() if toks else ""
        if first in _PS_DATA:
            part = re.sub(r"\x22(?:[^\x22`]|`.)*\x22|\x27(?:[^\x27]|\x27\x27)*\x27", '""', part)
        out.append(part)
    return "".join(out)


GSW = r"\.claude[/\\](?:hooks[/\\][^\s\x22\x27|;)]*|settings(?:\.local)?\.json)"
# Relative targets, used only when the working directory (or a Set-Location target) is .claude or .claude\hooks.
# The look-behind keeps an absolute path elsewhere (C:\work\x.py, $dir\x.py) from matching its file name.
_B = r"(?<![\w$./\\:-])"
GSW_REL_HOOKS = _B + r"(?:\.[/\\])?(?:[A-Za-z0-9_.-]+\.(?:py|sh|js)|harness-config\.json)(?![\w.-])"
GSW_REL_CLAUDE = _B + r"(?:\.[/\\])?(?:hooks[/\\][^\s\x22\x27|;)]+|settings(?:\.local)?\.json)(?![\w.-])"


def _gs_write(cmd, t):
    pats = [
        r"(?i)\b(?:Set-Content|Add-Content|Out-File|Clear-Content|Remove-Item|Rename-Item|New-Item|Tee-Object|sc|ac|ri|rni|ni|del|erase|rm|rmdir|rd|clc)\b[^;|\n]*" + t,
        r"(?i)\b(?:Copy-Item|Move-Item|cp|copy|cpi|mv|move|mi)\b[^;|\n]*(?:-Destination\s+[\x22\x27]?[^\s;|]*" + t
        + r"|\s[\x22\x27]?[^\s;|]*" + t + r"[^\s;|]*[\x22\x27]?\s*(?:$|[;|\n]))",
        r">[>]?\s*[\x22\x27]?[^\s;|]*" + t,
        r"(?i)\]::(?:WriteAll\w*|AppendAll\w*|Delete|Move|Copy|Replace|Create\w*|Open\w*)\s*\([^;\n]*" + t,
        r"(?i)StreamWriter[^;\n]*" + t,
        r"(?i)Invoke-(?:WebRequest|RestMethod)\b[^;|\n]*-OutFile\s+[\x22\x27]?[^\s;|]*" + t,
    ]
    if any(re.search(p, cmd) for p in pats):
        return True
    return bool(re.search(t, cmd, re.IGNORECASE) and re.search(PS_INTERP, cmd, re.IGNORECASE)
                and re.search(PS_INTERP_WRITE, cmd, re.IGNORECASE))


def check_guard_surface(cmd, cwd):
    if ADMIN:
        return
    cwd_n = (cwd or "").replace(chr(92), "/").rstrip("/")
    in_hooks = bool(re.search(r"/\.claude/hooks$", cwd_n, re.IGNORECASE))
    in_claude = bool(re.search(r"/\.claude$", cwd_n, re.IGNORECASE))
    for tgt in re.findall(r"(?i)(?:^|[;|&])\s*(?:Set-Location|cd|Push-Location|pushd|sl)\s+[\x22\x27]?([^;|&\s\x22\x27]+)", cmd):
        tgt = tgt.replace(chr(92), "/").rstrip("/").lower()
        if tgt.endswith(".claude/hooks") or (in_claude and tgt in ("hooks", "./hooks")):
            in_hooks = True
        elif tgt.endswith(".claude"):
            in_claude = True
    hit = re.search(GSW, cmd, re.IGNORECASE) and _gs_write(cmd, GSW)
    if not hit and in_hooks:
        hit = _gs_write(cmd, GSW_REL_HOOKS)
    if not hit and in_claude:
        hit = _gs_write(cmd, GSW_REL_CLAUDE)
    if hit:
        _block("READ-ONLY QA (PowerShell): writing the guard surface (.claude/hooks, .claude/settings*.json) "
               "is blocked. Edit settings.json / harness-config.json with the Write or Edit tool (the change is "
               "checked), or have a human start the session with QA_HARNESS_ADMIN=1 for hook maintenance.")


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
        if c[0].isalpha() and "-" not in c:
            # a short alias (md, rm, cp, sc ...) counts only in COMMAND position - `*.md` is not mkdir
            hit = bool(re.search(r"(?:^|[;|&({\n]\s*)" + re.escape(c) + r"(?![A-Za-z0-9_.-])", cmd, re.IGNORECASE))
        elif c[0].isalpha():
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
    if re.search(r"(?i)Directory\]::(?:Delete|Move|CreateDirectory)", cmd):
        _block("READ-ONLY QA (PowerShell): .NET Directory API delete/move/create with a protected repo in reach is blocked.")
    if re.search(r"(?:StreamWriter|BinaryWriter|TextWriter)", cmd):
        _block("READ-ONLY QA (PowerShell): .NET StreamWriter/BinaryWriter with a protected repo in reach is blocked.")
    if re.search(PS_INTERP, cmd_norm, re.IGNORECASE) and re.search(PS_INTERP_WRITE, cmd, re.IGNORECASE):
        _block("READ-ONLY QA (PowerShell): interpreter write with a protected repo in reach is blocked.")


def main():
    cmd, cwd = _read_command()
    if not cmd:
        sys.exit(0)
    scan = strip_herestring_bodies(cmd)   # literal bodies are DATA, not commands
    check_opaque(scan)
    check_guard_surface(scan, cwd)
    scan_git = mask_inert_quotes(scan)    # quoted text given to a data-only cmdlet is not a command
    if not owned_context(scan_git, cwd):
        check_git_mutations(scan_git)
        check_npm_mutations(scan_git)
    check_source_repo_writes(scan, cwd)
    sys.exit(0)


if __name__ == "__main__":
    main()
