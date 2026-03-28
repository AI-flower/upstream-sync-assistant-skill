---
name: upstream-sync-assistant
description: Use when working in a forked repository with an upstream mirror branch and an internal integration branch, and you need to bootstrap sync configuration, audit mirror pollution, prepare a local upstream merge, analyze upstream drift, or generate sync risk reports.
---

# Upstream Sync Assistant

## Overview

Use this skill for repositories that keep an internal long-lived branch on top of an upstream open-source project. The skill standardizes local sync preparation, deterministic checks, merge-time artifact collection, and report generation while stopping before remote writes or mirror-branch changes.

## When to Use

- The repository has one upstream read-only remote and one internal writable remote.
- One branch should remain a mirror of upstream.
- Another long-lived branch carries internal changes.
- You need to bootstrap `.upstream-sync.yml`.
- You need to check whether the mirror branch is polluted.
- You need to create a sync branch and merge upstream locally.
- You need a structured sync report or PR draft.

Do not use this skill for ordinary feature branches or for repositories without an upstream/integration split.

## Core Workflow

1. If `.upstream-sync.yml` is missing or invalid, run `python3 scripts/bootstrap_repo.py --repo <target-repo>` and confirm the inferred config summary before writing it.
2. Run `python3 scripts/doctor.py --repo <target-repo>` before any sync preparation. Stop on hard-stop conditions.
3. Run `python3 scripts/prepare_sync.py --repo <target-repo>` to fetch upstream, create a timestamped run directory, and create a local sync branch from the integration branch.
4. Run `python3 scripts/collect_git_facts.py --repo <target-repo> --run-dir <run-dir>` to gather facts for risk analysis.
5. Run `python3 scripts/merge_sync.py --repo <target-repo> --run-dir <run-dir>` to merge upstream locally into the sync branch.
6. Run `python3 scripts/verify_checks.py --repo <target-repo> --run-dir <run-dir>` to execute configured verification commands.
7. Run `python3 scripts/render_report.py --repo <target-repo> --run-dir <run-dir>` to generate `risk-report.md` and `pr-draft.md`.

## Safety Rules

- Never push automatically.
- Never modify the mirror branch automatically.
- Never change git remotes automatically.
- If `doctor` reports hard stops, do not continue.
- If verification fails, stop and surface the failing commands before any manual next step.

## Files To Read As Needed

- Config semantics: `references/config-schema.md`
- Stage behavior and stop conditions: `references/lifecycle.md`
- Risk labels for analysis: `references/risk-categories.md`
- Report structure: `references/report-format.md`

## Bundled Assets

- Example repository config: `assets/upstream-sync.example.yml`
- Install helper: `install.sh`
- Uninstall helper: `uninstall.sh`
