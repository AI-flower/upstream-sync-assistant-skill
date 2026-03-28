# Config Schema

The repository-local config file is `.upstream-sync.yml`.

Required fields:

- `version`
- `git.upstream_remote`
- `git.write_remote`
- `git.mirror_branch`
- `git.integration_branch`
- `git.sync_branch_prefix`
- `policy.require_clean_worktree`
- `policy.require_confirmation_for_push`
- `policy.require_confirmation_for_mirror_branch_change`
- `policy.block_push_to_upstream`
- `validation.post_merge_checks`
- `validation.manual_checks`
- `reporting.output_dir`

Optional fields:

- `sync.cadence_days`
- `sync.freeze_windows`
- `analysis.high_risk_paths`
- `analysis.high_risk_files`
- `analysis.infra_keywords`
- `analysis.customizations_registry`
- `reporting.pr_template`

The parser supports a narrow YAML subset:

- nested mappings
- lists
- booleans
- integers
- quoted or plain strings

It does not support anchors, multiline blocks, or advanced YAML syntax.
