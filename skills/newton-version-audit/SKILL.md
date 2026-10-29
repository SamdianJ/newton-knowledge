---
name: newton-version-audit
description: Audit a Newton knowledge-base snapshot against a specified Newton source tree, installed environment, or evidence collected on another computer. Identify source/API/default drift, affected knowledge and paper mappings, and experiments needed before claiming compatibility. Use for Newton version upgrades, downgrades, forks, local patches, or environment compatibility checks.
---

# Newton Version Audit

Determine whether the current knowledge applies to the requested Newton target. Separate source equivalence, API migration, backend/runtime compatibility, and physical-result reproducibility. Matching version strings or successful imports are insufficient to establish compatibility.

## Identify the two sides

- Accept either the developer knowledge root or the portable repository root containing `knowledge-base/`. Read `knowledge/current.json`, its hash-verified build manifest, and `manifests/source-lock.json`. Use the active snapshot's catalog for experiment counts; historical release summaries may be stale.
- For a local target, prefer the user's actual Python interpreter (`collect --installed`) or explicitly selected source checkout (`collect --source`). A checkout is not proof of what another environment imports.
- For another computer, send the standalone collector script and have it run with that computer's target interpreter. Read [the command reference](references/commands.md) for collection, transfer and report examples. Do not assume access to that computer or install/upgrade Newton there.
- If only a version/tag is supplied, record it as a claim. Obtain its exact upstream commit/source or the user's environment evidence before asserting compatibility. For an upstream comparison, use the official Newton repository and resolve the requested ref; do not substitute latest/main. A tag snapshot cannot rule out local patches on another computer.

## Collect and compare

Run `scripts/newton_version_audit.py` with Python 3.10+ (3.12 recommended). It uses the standard library, never imports Newton, and does not run simulation, install dependencies, fetch code, or modify the knowledge snapshot. Use the actual target interpreter when auditing an installed environment.

The collector records relative-file hashes, Python AST declarations/default expressions, version sources, an exact-root Git identity when available, and selected installed dependency versions. Scan/parse gaps are reported instead of silently treated as absence. Transfer JSON contains no full source files, credentials, host name or absolute source paths; review it before sharing because it contains file names and declaration expressions. Its checksum detects accidental corruption, not sender authenticity.

The comparator verifies the active baseline, compares files/declarations within the observed scope, and traces changed source references into knowledge records and one-hop graph neighbors. Save reports under `.local/version-audit/` or another output directory; existing reports are never overwritten.

Treat generated JSON/Markdown as triage, not a final semantic verdict. Read [the review criteria](references/review-criteria.md) and inspect relevant implementation excerpts before deciding which explanations or parameter advice must change. Hash-only evidence identifies a review requirement but cannot explain a changed algorithm. Impact lists are source-reference mappings, not a complete dependency graph.

## Report the decision

State the baseline build/version/commit and the target's observed version/commit/dirty status, collection scope and environment gaps. Distinguish:

- **Source equivalent in the observed scope:** no source rewrite indicated within that scope; runtime and physical results remain unverified.
- **Review required:** source, declarations, exports, dependencies or version metadata differ. Identify concrete records and what to inspect, adapt or re-index. A changed file is not itself proof of a broken API.
- **Evidence incomplete:** version-only input, absent source, partial scans, parse failures or unresolved identity prevent the relevant conclusion.
- **Invalid baseline:** snapshot/release integrity fails; resolve it before comparing.

Give a prioritized action table: evidence → affected API/parameter/knowledge/paper mapping → confirmed incompatibility or review question → proposed adaptation → validation needed. Do not call untested items compatible. If an older target lacks a solver/feature, mark that knowledge unavailable for it; do not describe a broken installation without evidence.

Never inherit saved experiments as measurements of a different environment. Even identical source requires checking backend versions, device, precision, dt/substeps, units, scenes and metrics. Define acceptance criteria before proposing reruns and preserve negative results. Distinguish a paper's validity from changes to its implementation mapping or assumptions.

Default to an audit and adaptation plan. If fixes are also requested, edit authoring sources in a separate target-version workflow, preserve version-scoped evidence, rebuild and validate that candidate. Do not change the pinned lock, published snapshot or current pointer merely to pass integrity checks. This skill does not authorize remote publication or pushing changes.
