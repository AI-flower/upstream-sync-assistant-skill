# Lifecycle

The skill uses a fixed stage model:

1. `bootstrap`
2. `doctor`
3. `prepare`
4. `analyze`
5. `merge`
6. `verify`
7. `report`

Hard-stop conditions:

- invalid or missing config
- polluted mirror branch
- dirty worktree when policy requires clean state
- missing required remote or branch

Soft-stop conditions:

- cadence exceeded
- infrastructure changes detected
- merge conflicts
- verification failures

Explicit confirmation is required before:

- changing the mirror branch
- pushing any remote branch
- force pushing
- overwriting repository config
