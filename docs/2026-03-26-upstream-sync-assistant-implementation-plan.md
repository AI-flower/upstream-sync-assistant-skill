# Upstream Sync Assistant Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a globally installable upstream-sync-assistant skill project with repository-local configuration, deterministic support scripts, and report generation for safe local upstream sync workflows.

**Architecture:** The project ships a single globally installable skill plus Python helper scripts. The skill reads a repository-local `.upstream-sync.yml`, runs staged local sync operations, writes run artifacts under `.upstream-sync/runs/<timestamp>/`, and stops before remote writes or mirror-branch changes. The scripts provide deterministic facts; the skill guidance and references explain how to interpret and use them.

**Tech Stack:** Markdown, Python 3 standard library, shell install scripts, YAML-like config via JSON-compatible parser subset and line-based parsing

---

## Chunk 1: Project Skeleton

### Task 1: Create project layout and top-level assets

**Files:**
- Create: `SKILL.md`
- Create: `assets/upstream-sync.example.yml`
- Create: `references/config-schema.md`
- Create: `references/lifecycle.md`
- Create: `references/report-format.md`
- Create: `references/risk-categories.md`
- Create: `install.sh`
- Create: `uninstall.sh`
- Create: `.gitignore`

- [ ] **Step 1: Define the file layout in the project folder**

Create the canonical skill project structure with `docs/`, `scripts/`, `references/`, `assets/`, and `tests/`.

- [ ] **Step 2: Write the skill trigger and workflow document**

Write `SKILL.md` so the skill triggers on upstream sync requests, bootstrap requests, and fork drift analysis.

- [ ] **Step 3: Add install assets**

Provide an example config file and install/uninstall scripts for global skill placement.

## Chunk 2: Deterministic Script Layer

### Task 2: Implement shared support code

**Files:**
- Create: `scripts/common.py`
- Test: `tests/test_common.py`

- [ ] **Step 1: Write a failing config and command test**

Add tests for reading the repository config, running git commands, and timestamped run directory creation.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest tests.test_common -v`
Expected: FAIL because the module does not exist yet.

- [ ] **Step 3: Implement minimal shared helpers**

Add functions for:
- locating repo root
- loading `.upstream-sync.yml`
- running git commands
- writing JSON and Markdown artifacts
- creating a run directory

- [ ] **Step 4: Re-run the tests**

Run: `python3 -m unittest tests.test_common -v`
Expected: PASS

### Task 3: Implement bootstrap and doctor scripts

**Files:**
- Create: `scripts/bootstrap_repo.py`
- Create: `scripts/doctor.py`
- Test: `tests/test_bootstrap_and_doctor.py`

- [ ] **Step 1: Write failing bootstrap and doctor tests**

Cover:
- remote and branch discovery
- bootstrap candidate inference
- mirror branch pollution detection
- dirty worktree detection

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest tests.test_bootstrap_and_doctor -v`
Expected: FAIL because the scripts are not implemented yet.

- [ ] **Step 3: Implement minimal bootstrap and doctor behavior**

Emit structured JSON and use non-zero exit codes for hard-stop conditions.

- [ ] **Step 4: Re-run the tests**

Run: `python3 -m unittest tests.test_bootstrap_and_doctor -v`
Expected: PASS

### Task 4: Implement prepare, git-facts, merge, verify, and report scripts

**Files:**
- Create: `scripts/prepare_sync.py`
- Create: `scripts/collect_git_facts.py`
- Create: `scripts/merge_sync.py`
- Create: `scripts/verify_checks.py`
- Create: `scripts/render_report.py`
- Test: `tests/test_flow_scripts.py`

- [ ] **Step 1: Write failing flow tests**

Cover:
- sync branch naming
- context artifact creation
- git facts summary generation
- merge conflict JSON shape
- verification command result recording
- markdown report rendering

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest tests.test_flow_scripts -v`
Expected: FAIL because the scripts are not implemented yet.

- [ ] **Step 3: Implement minimal flow scripts**

Use shared helpers and write all outputs under `.upstream-sync/runs/<timestamp>/`.

- [ ] **Step 4: Re-run the tests**

Run: `python3 -m unittest tests.test_flow_scripts -v`
Expected: PASS

## Chunk 3: Validation and Packaging

### Task 5: Verify the skill project end-to-end

**Files:**
- Modify: `docs/2026-03-26-upstream-sync-assistant-implementation-plan.md`

- [ ] **Step 1: Run the full test suite**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 2: Smoke-check script help and file layout**

Run:
- `python3 scripts/bootstrap_repo.py --help`
- `python3 scripts/doctor.py --help`
- `find . -maxdepth 2 -type f | sort`

Expected:
- help text prints without tracebacks
- required files are present

- [ ] **Step 3: Commit**

```bash
git add .
git commit -m "feat: implement upstream sync assistant skill project"
```
