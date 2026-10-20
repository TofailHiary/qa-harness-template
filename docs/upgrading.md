# Upgrading

## Upgrading an installed harness to a newer template

1. Pull the new template version.
2. Re-run the installer against the project:
   ```bash
   python qa-harness-template/scripts/install.py --target /path/to/your/project --full
   ```
   It replaces skills, agents, hooks, rules, references and docs with the new versions and **preserves**
   `PROJECT-PROFILE.md`, `settings.json`, `harness-config.json`, `.mcp.json`, `.gitignore` and
   `.gitattributes`, writing the new template version next to each as `<name>.new`.
3. Diff each `*.new` against your file and merge what you want (new profile sections such as §14–§18,
   new hook wiring in `settings.json`, new keys such as `owned_repos` / `gate` in `harness-config.json`).
   Delete the `*.new` files afterwards (they are git-ignored).
4. If you rebound the DB tool id (non-MySQL engines), run `/configure-project` again so the new skills are
   rebound too.
5. Run `python scripts/validate.py --installed` and `python scripts/hook-redteam/runner.py --hooks
   <project>/.claude/hooks`.
6. Read `CHANGELOG.md` for behaviour changes (for example the Bash guard became an allow-list of git
   verbs in 2.0, and git write denies moved from `settings.json` into the hooks).

## Upgrading from 1.x to 2.0

- `PROJECT-PROFILE.md` gained §14–§18 and extra fields in §2 (`Demo`), §6, §7, §9, §10, §11, §12, §13.
  Copy your 1.x answers into the 2.0 file; the installer leaves `PROJECT-PROFILE.md.new` for that.
- `settings.json` wires three new hooks (GitHub writes, Stop, SubagentStop) and no longer denies
  `git commit/push/checkout` itself (the hooks do, per repo). Merge from `settings.json.new`.
- `harness-config.json` gained `owned_repos` and `gate`. Missing keys default safely (no owned repos,
  gate advisory).
- Five reference stubs under `.claude/references/` were retired; `system-map.md` replaces them.
- The evidence folder convention is now one folder per run: `qa-evidence/<KEY or BUG-id>-<yyyymmdd>/`.

## Pulling future changes from a private source setup into the template

See `docs/maintainers/generalization-conventions.md` §8: diff, classify each hunk (port / rebind /
drop), run `scripts/validate.py` and the hook suite, update `catalog.json` + `docs/catalog.md`
(`python scripts/validate.py --fix-catalog-doc`) and `CHANGELOG.md`. Never copy memory, evidence,
backups or logs.
