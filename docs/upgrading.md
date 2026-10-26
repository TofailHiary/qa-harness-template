# Upgrading

## Upgrading an installed harness to a newer template

1. Pull the new template version.
2. Re-run the installer against the project:
   ```bash
   python qa-harness-template/scripts/install.py --target /path/to/your/project --full
   ```
   It replaces skills, agents, hooks, rules, references and docs with the new versions and **preserves**
   `PROJECT-PROFILE.md`, `settings.json`, `harness-config.json`, `tool-bindings.json`, `.mcp.json`,
   `.gitignore` and `.gitattributes`, writing the new template version next to each as `<name>.new`. It then
   re-applies `.claude/tool-bindings.json`, so a DB-tool rebinding survives the upgrade.
3. Diff each `*.new` against your file and merge what you want (new profile sections such as §14–§18,
   new hook wiring in `settings.json`, new keys such as `owned_repos` / `gate` in `harness-config.json`).
   Delete the `*.new` files afterwards (they are git-ignored).
4. DB tool rebinding is re-applied automatically (2.1+). Coming from 2.0 with a rebound tool, record it
   once: `python .claude/scripts/rebind.py --db <your tool id>`; `rebind.py --check` must print OK.
5. Run `python .claude/scripts/doctor.py` (must print READY), then `python scripts/validate.py --installed`
   and `python scripts/hook-redteam/runner.py --hooks <project>/.claude/hooks`.
6. Read `CHANGELOG.md` for behaviour changes (for example the Bash guard became an allow-list of git
   verbs in 2.0, and git write denies moved from `settings.json` into the hooks).

## Upgrading from 2.0 to 2.1

1. Run the installer as above. `settings.json` is preserved, so **merge `settings.json.new`**: every Python
   hook command becomes `sh "$CLAUDE_PROJECT_DIR/.claude/hooks/run-hook.sh" <script>.py` (the Stop hooks add
   `--fail-open`), the Write guard's matcher gains `MultiEdit`, and the deny list gains `Read(.mcp.json)`.
   `doctor.py` reports FAIL until the merge is done. Making the merge with the Write tool passes the new
   content check, because every guard hook is still present afterwards.
2. Re-render `.mcp.json`: `python .claude/scripts/render_mcp.py`. Versions are now pinned, the Windows
   `cmd /c` wrapper is added automatically, and servers you added are kept.
3. Orchestrators now keep `qa-evidence/<run-folder>/run.json`; nothing to migrate - old runs simply have none.
4. Hook maintenance from inside a session now needs a human: edit the hook files yourself, or start Claude
   Code with `QA_HARNESS_ADMIN=1` for that session only.

## Bumping pinned MCP versions

1. `python scripts/check_deps.py --online` lists every pin next to the newest published version.
2. Change the pin, set its `_tested` note to what you actually exercised, re-render with `render_mcp.py`.
3. Restart Claude Code, run `/env-health` and one skill per capability; only then commit the new pin.

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
