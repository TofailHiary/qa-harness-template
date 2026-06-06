#!/usr/bin/env python3
"""PreToolUse Bash - READ-ONLY QA (portable).
Blocks mutating git/npm subcommands and writes into protected source repos
(folder names from harness-config.json -> protected_repos)."""
import json
import re
import sys
import harness_config as hc

MUTATING_VERBS = ['commit', 'push', 'merge', 'rebase', 'cherry-pick', 'am', 'apply',
                  'restore', 'checkout', 'switch', 'add', 'update-ref', 'clean', 'rm', 'mv']
MUTATING_NPM_VERBS = ['publish', 'version', 'ci']


def block(reason):
    sys.stdout.write(json.dumps({'decision': 'block', 'reason': reason}))
    sys.exit(2)


def read_cmd():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            block('READ-ONLY QA: empty Bash hook input. Blocked.')
        data = json.loads(raw)
    except Exception as e:
        block('READ-ONLY QA: bad Bash hook input (' + type(e).__name__ + '). Blocked.')
        return ''
    return (data.get('tool_input', {}) or {}).get('command', '') or ''


def check_git(cmd):
    for sub in MUTATING_VERBS:
        if re.search(r'(?i)(?:^|[^A-Za-z])git\s+' + re.escape(sub) + r'(?:\s|$|[^A-Za-z])', cmd):
            block('READ-ONLY QA: git ' + sub + ' is blocked. Session is read-only on source repos.')
    if re.search(r'(?i)(?:^|[^A-Za-z])git\s+reset\s+--hard', cmd):
        block('READ-ONLY QA: git reset --hard is blocked.')
    if re.search(r'(?i)(?:^|[^A-Za-z])git\s+stash\s+(pop|apply|drop|clear)', cmd):
        block('READ-ONLY QA: git stash mutating op is blocked.')
    if re.search(r'(?i)(?:^|[^A-Za-z])git\s+branch\s+(-D|-d|-m|-M|--delete|--move)', cmd):
        block('READ-ONLY QA: git branch delete/rename is blocked.')
    if re.search(r'(?i)(?:^|[^A-Za-z])git\s+tag\s+(-d|--delete)', cmd):
        block('READ-ONLY QA: git tag delete is blocked.')


def check_npm(cmd):
    for sub in MUTATING_NPM_VERBS:
        if re.search(r'(?i)(?:^|[^A-Za-z])npm\s+' + sub + r'(?:\s|$|[^A-Za-z])', cmd):
            block('READ-ONLY QA: npm ' + sub + ' is blocked.')


def check_writes(cmd_norm, repos):
    if not repos:
        return
    alt = '(' + '|'.join(re.escape(d) for d in repos) + ')'
    into = '/(?:' + '|'.join(re.escape(d) for d in repos) + ')'
    if not re.search('/' + alt + r'(?:/|$|\s|[^A-Za-z0-9_-])', cmd_norm, re.IGNORECASE):
        return
    if re.search(r'>>?\s*[^|<>\n]*' + into, cmd_norm, re.IGNORECASE):
        block('READ-ONLY QA: redirection into a protected repo is blocked.')
    if re.search(r'\|\s*tee\b', cmd_norm, re.IGNORECASE):
        block('READ-ONLY QA: tee into a protected repo is blocked.')
    if re.search(r'(?:^|[^A-Za-z])sed\s+-i', cmd_norm, re.IGNORECASE):
        block('READ-ONLY QA: sed -i on a protected repo is blocked.')
    if re.search(r'(?:^|[^A-Za-z])dd\s+[^|]*of=', cmd_norm, re.IGNORECASE):
        block('READ-ONLY QA: dd of= on a protected repo is blocked.')
    if re.search(r'(?:^|[^A-Za-z])rm\s+(-[rRfF]+)', cmd_norm):
        block('READ-ONLY QA: rm -r/-rf touching a protected repo is blocked.')
    if re.search(r'(?:^|[^A-Za-z])(mv|cp)\s+[^|]+\s+[^\s]*' + into, cmd_norm, re.IGNORECASE):
        block('READ-ONLY QA: mv/cp into a protected repo is blocked.')


def main():
    cmd = read_cmd()
    if not cmd:
        sys.exit(0)
    repos = hc.load().get("protected_repos", [])
    cmd_norm = cmd.replace('\\', '/')
    check_git(cmd)
    check_npm(cmd)
    check_writes(cmd_norm, repos)
    sys.exit(0)


if __name__ == '__main__':
    main()
