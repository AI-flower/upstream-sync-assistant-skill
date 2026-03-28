# Report Format

Each run writes reports under `.upstream-sync/runs/<timestamp>/`.

Required artifacts:

- `context.json`
- `doctor.json`
- `git-facts.json`
- `merge.json`
- `verify.json`
- `risk-report.md`
- `pr-draft.md`

`risk-report.md` should contain:

- sync summary
- upstream range
- high-risk file and path hits
- merge outcome
- verification outcome
- manual follow-up items

`pr-draft.md` should contain:

- proposed title
- sync range
- key upstream changes
- risk notes
- verification notes
