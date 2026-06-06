#!/usr/bin/env python3
"""PreToolUse PowerShell - READ-ONLY QA (portable).
Closes the PowerShell gap that would bypass block-bash-writes. Blocks mutating
git/npm and PowerShell/.NET writes into protected source repos (folder names
from harness-config.json -> protected_repos)."""
import json
import re
import sys
import harness_config as hc

MUTATING_GIT = ["commit", "push", "merge", "rebase", "cherry-pick", "am", "apply",
                "restore", "checkout", "switch", "add", "rm", "mv", "update-ref", "clean"]
MUTATING_NPM = ["publish", "version", "ci"]
MUTATING_PS_CMDLETS = ["Set-Content", "Out-File", "Add-Content", "New-Item", "Set-ItemProperty",
                       "Move-Item", "Copy-Item", "Remove-Item", "Clear-Content", "Rename-Item"]


def block(reason):
    sys.stdout.write(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(2)


def read_command():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            block("READ-ONLY QA: empty PowerShell hook input. Blocked.")
        data = json.loads(raw)
    except Exception as e:
        block("READ-ONLY QA: bad PowerShell hook input (%s). Blocked." % type(e).__name__)
        return ""
    return (data.get("tool_input", {}) or {}).get("command", "") or ""


def check_git(cmd):
    for sub in MUTATING_GIT:
        if re.search(r"(?i)(?:^|[^A-Za-z])git\s+" + re.escape(sub) + r"(?:\s|$|['\";&|])", cmd):
            block("READ-ONLY QA (PowerShell): git %s is blocked." % sub)
    if re.search(r"(?i)(?:^|[^A-Za-z])git\s+reset\s+--hard", cmd):
        block("READ-ONLY QA (PowerShell): git reset --hard is blocked.")
    if re.search(r"(?i)(?:^|[^A-Za-z])git\s+stash\s+(pop|apply|drop|clear)", cmd):
        block("READ-ONLY QA (PowerShell): git stash pop/apply/drop/clear is blocked.")
    if re.search(r"(?i)(?:^|[^A-Za-z])git\s+branch\s+(-D|-d|-m|-M|--delete|--move)", cmd):
        block("READ-ONLY QA (PowerShell): git branch delete/rename is blocked.")
    if re.search(r"(?i)(?:^|[^A-Za-z])git\s+tag\s+(-d|--delete)", cmd):
        block("READ-ONLY QA (PowerShell): git tag delete is blocked.")


def check_npm(cmd):
    for sub in MUTATING_NPM:
        if re.search(r"(?i)(?:^|[^A-Za-z])npm\s+" + sub + r"(?:\s|$|['\";&|])", cmd):
            block("READ-ONLY QA (PowerShell): npm %s is blocked." % sub)


def check_repo_writes(cmd, repos):
    if not repos:
        return
    pat = "(" + "|".join(re.escape(d) for d in repos) + ")"
    if not re.search(r"[/\\]" + pat + r"[/\\]", cmd, re.IGNORECASE):
        return
    for cmdlet in MUTATING_PS_CMDLETS:
        if re.search(r"(?i)(?:^|[^A-Za-z])" + re.escape(cmdlet) + r"(?:\s|$|-)", cmd):
            block("READ-ONLY QA (PowerShell): %s with a protected repo path is blocked." % cmdlet)
    if re.search(r">[>]?\s*\"?[^|<>\"]*[/\\]" + pat, cmd, re.IGNORECASE):
        block("READ-ONLY QA (PowerShell): output redirection into a protected repo is blocked.")
    if re.search(r"(?:\[System\.IO\.)?File(?:\]::|\.)+?(?:WriteAllText|WriteAllBytes|AppendAllText|"
                 r"AppendAllLines|Create|Copy|Delete|Move|Open)", cmd):
        block("READ-ONLY QA (PowerShell): .NET File API write/delete/move into a protected repo is blocked.")
    if re.search(r"(?:StreamWriter|BinaryWriter|TextWriter)", cmd):
        block("READ-ONLY QA (PowerShell): .NET StreamWriter/BinaryWriter into a protected repo is blocked.")


def main():
    cmd = read_command()
    if not cmd:
        sys.exit(0)
    repos = hc.load().get("protected_repos", [])
    check_git(cmd)
    check_npm(cmd)
    check_repo_writes(cmd, repos)
    sys.exit(0)


if __name__ == "__main__":
    main()
