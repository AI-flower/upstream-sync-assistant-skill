# Risk Categories

Use these categories when summarizing sync risk:

- `mirror-pollution`: the mirror branch has commits not present upstream.
- `coupling`: internal customizations overlap heavily with changed upstream areas.
- `semantic`: textual merge succeeds but behavior may drift.
- `infra`: dependency, build, runtime, or environment changes may widen blast radius.
- `conflict`: merge conflicts require manual resolution.
- `cadence`: upstream drift is large enough that sync scope is risky.

Suggested severities:

- `low`: small diff, no high-risk hits
- `medium`: one or two high-risk hits or cadence warning
- `high`: infra hits, merge conflicts, or repeated customization overlap
- `critical`: polluted mirror branch or verification failure in core checks
