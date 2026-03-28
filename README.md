# upstream-sync-assistant-skill

一个面向 Codex / Claude Code 的上游同步技能与脚本工具集，用于在“上游镜像分支 + 内部长线集成分支”的仓库中，标准化同步准备、风险分析、验证和报告生成。  
A skill and script bundle for Codex / Claude Code that standardizes sync preparation, risk analysis, verification, and report generation for repositories that keep a clean upstream mirror branch plus a long-lived internal integration branch.

## 适用场景 / When To Use

- 仓库同时存在只读上游 remote 和可写内部 remote。  
  The repository has one read-only upstream remote and one writable internal remote.
- 你希望保留一个尽量干净的镜像分支，并在另一个长期分支上承载内部改动。  
  You want one branch to stay as close to upstream as possible while another long-lived branch carries internal changes.
- 你希望在真正推送或提 PR 之前，先完成本地同步准备、风险分析和验证。  
  You want deterministic local preparation, risk analysis, and verification before any push or PR.

## 项目作用 / What This Repository Does

- `scripts/bootstrap_repo.py`: 检查目标仓库并推断同步配置候选；inspect the target repository and infer sync configuration candidates.
- `scripts/doctor.py`: 在缺少配置、remote、分支、工作区不干净或镜像分支被污染时直接阻断；stop on hard-stop conditions such as missing config, missing remotes or branches, dirty worktrees, or polluted mirror branches.
- `scripts/prepare_sync.py`: 拉取上游、创建时间戳运行目录，并从集成分支切出本地同步分支；fetch upstream, create a timestamped run directory, and create a local sync branch from the integration branch.
- `scripts/collect_git_facts.py`: 收集提交、变更文件和高风险命中信息；collect commit, file-diff, and high-risk hit data.
- `scripts/merge_sync.py`: 在本地同步分支上执行合并并记录冲突信息；perform the local merge and record conflict details.
- `scripts/verify_checks.py`: 运行配置中的合并后检查命令并记录手工检查项；run configured post-merge checks and record manual follow-up items.
- `scripts/render_report.py`: 生成 `risk-report.md` 和 `pr-draft.md`；render `risk-report.md` and `pr-draft.md`.

## 工作流 / Workflow

1. `bootstrap`: 推断目标仓库的同步配置候选。  
   Infer sync configuration candidates for the target repository.
2. `doctor`: 在真正准备同步前执行硬性检查。  
   Run hard-stop preflight checks before preparing a sync.
3. `prepare`: 创建运行目录并生成本地同步分支。  
   Create the run directory and the local sync branch.
4. `analyze`: 收集上游提交范围内的结构化 Git 信息。  
   Collect structured Git facts for the upstream range.
5. `merge`: 将上游镜像分支合并到本地同步分支。  
   Merge the upstream mirror target into the prepared sync branch.
6. `verify`: 执行自动检查并记录人工检查项。  
   Execute automated checks and record manual checks.
7. `report`: 输出风险报告和 PR 草稿。  
   Produce the risk report and PR draft.

## 安装 / Installation

这个仓库既可以作为 skill 安装，也可以直接运行其中的 Python 脚本。  
This repository can be installed as a skill or used directly by running its Python scripts.

```bash
git clone git@github.com:AI-flower/upstream-sync-assistant-skill.git
cd upstream-sync-assistant-skill
./install.sh
```

`install.sh` 会创建以下符号链接：  
`install.sh` creates symlinks at:

- `~/.agents/skills/upstream-sync-assistant`
- `~/.codex/skills/upstream-sync-assistant`

脚本本身没有声明第三方 Python 依赖，默认依赖 Python 3 和 Git。  
The helper scripts in this repo do not declare third-party Python dependencies; they rely on Python 3 and Git.

## 快速开始 / Quick Start

下面假设目标仓库位于 `/path/to/target-repo`。  
The example below assumes the target repository lives at `/path/to/target-repo`.

```bash
# 1) 检查目标仓库 / Inspect the target repository
python3 scripts/bootstrap_repo.py --repo /path/to/target-repo

# 2) 写入推断配置 / Write the inferred config
python3 scripts/bootstrap_repo.py --repo /path/to/target-repo --write-config

# 3) 运行预检 / Run preflight checks
python3 scripts/doctor.py --repo /path/to/target-repo

# 4) 准备同步分支 / Prepare the sync branch
python3 scripts/prepare_sync.py --repo /path/to/target-repo
```

`prepare_sync.py` 会输出 JSON，其中包含 `run_dir`。将这个值带入后续步骤：  
`prepare_sync.py` prints JSON that includes `run_dir`. Use that value in the remaining steps:

```bash
RUN_DIR="/path/to/target-repo/.upstream-sync/runs/<run-id>"

python3 scripts/collect_git_facts.py --repo /path/to/target-repo --run-dir "$RUN_DIR"
python3 scripts/merge_sync.py --repo /path/to/target-repo --run-dir "$RUN_DIR"
python3 scripts/verify_checks.py --repo /path/to/target-repo --run-dir "$RUN_DIR"
python3 scripts/render_report.py --repo /path/to/target-repo --run-dir "$RUN_DIR"
```

最终你会得到结构化产物和 Markdown 报告。  
At the end of the run you will have structured artifacts plus Markdown reports.

## 配置文件 / Repository Config

仓库级配置文件名为 `.upstream-sync.yml`。完整示例见 [assets/upstream-sync.example.yml](assets/upstream-sync.example.yml)。  
The repository-local configuration file is `.upstream-sync.yml`. A full example is available at [assets/upstream-sync.example.yml](assets/upstream-sync.example.yml).

一个最小可读示例如下：  
A compact example looks like this:

```yaml
version: 1

git:
  upstream_remote: upstream
  write_remote: origin
  mirror_branch: main
  integration_branch: yl-main
  sync_branch_prefix: sync/upstream-

policy:
  require_clean_worktree: true
  require_confirmation_for_push: true
  require_confirmation_for_mirror_branch_change: true
  block_push_to_upstream: true

validation:
  post_merge_checks:
    - yarn test
  manual_checks:
    - core login flow

reporting:
  output_dir: docs/upstream-sync/reports
```

## 安全边界 / Safety Rules

- 不会自动推送任何远程分支。  
  It never pushes automatically.
- 不会自动修改镜像分支。  
  It never changes the mirror branch automatically.
- 不会自动改写 Git remote 配置。  
  It never rewrites Git remotes automatically.
- `doctor` 遇到关键问题时会直接停止。  
  `doctor` stops immediately on hard-stop conditions.
- 推送、镜像分支改动、强推和覆盖配置都应该经过明确确认。  
  Pushing, changing the mirror branch, force pushing, and overwriting config should require explicit confirmation.

## 输出产物 / Outputs

- `.upstream-sync.yml`: 仓库本地配置。  
  Repository-local config.
- `context.json`: 一次同步运行的上下文。  
  Context for a sync run.
- `git-facts.json`: 提交和文件级分析结果。  
  Commit and file-level analysis results.
- `merge.json`: 合并结果和冲突信息。  
  Merge results and conflict details.
- `verify.json`: 自动检查结果和手工检查项。  
  Automated check results and manual follow-up items.
- `risk-report.md`: 风险摘要。  
  Risk summary.
- `pr-draft.md`: PR 描述草稿。  
  Draft PR content.

## 项目结构 / Project Structure

- [SKILL.md](SKILL.md): skill 入口定义。  
  Skill entry point and workflow rules.
- [scripts/](scripts): Python 脚本实现。  
  Python implementation.
- [references/](references): 配置、生命周期和报告格式说明。  
  Reference docs for config, lifecycle, and report format.
- [assets/](assets): 示例配置等静态资产。  
  Static assets such as example config files.
- [tests/](tests): 单元测试和流程测试。  
  Unit and flow tests.

## 开发与测试 / Development And Tests

如果你要修改脚本或 skill 定义，建议先运行测试：  
If you modify the scripts or the skill definition, run the test suite first:

```bash
python3 -m unittest discover -s tests
```

如果你只想浏览设计边界和阶段定义，可以先看这些参考文档：  
If you want the design boundaries and stage model first, start with these references:

- [references/config-schema.md](references/config-schema.md)
- [references/lifecycle.md](references/lifecycle.md)
- [references/report-format.md](references/report-format.md)
- [references/risk-categories.md](references/risk-categories.md)
