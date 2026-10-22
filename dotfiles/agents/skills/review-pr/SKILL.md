---
name: review-pr
description: Review or re-review a pull request in any repository, tracing cross-package effects in monorepos and delivering evidence-based findings only in chat.
---

# Review a pull request

Keep the review read-only and deliver the complete result in chat. Do not edit
source, change branches or worktrees, modify Git state, or publish comments or
reviews on the hosting service. Use available repository connectors when sufficient
or other read-only access supported by the environment.

## Establish the exact candidate

Identify the repository and PR, pin the current base and head SHAs, and inspect the
actual comparison used by the PR. Read its description, relevant comments, author
responses, and explicit review exclusions. Treat these as context to verify.

Read files at the pinned revisions. Before reporting, check whether the head has
changed; review the delta or clearly identify the inspected snapshot and resulting
limitation rather than mixing evidence from different revisions.

Read applicable repository guidance from the baseline revision and discover nested
instructions and documentation for the affected areas. Do not assume particular
instruction paths, directory names, languages, frameworks, or workspace tools.
Inspect changes to guidance as part of the candidate being reviewed.

Cover the full requested scope, resolving pagination or truncation before claiming
coverage. Prioritize consequential behavior without stopping at the first finding
or imposing an arbitrary limit on confirmed findings. Record inaccessible areas
and unresolved questions as limitations.

## Trace the affected behavior

Understand the change's intent, entry points, decision owners, state, failures,
and relevant tests. In a monorepo, inspect workspace manifests and dependency
relationships to identify affected apps, services, libraries, and shared tooling.

Follow changed contracts through producers and direct or indirect consumers,
including unchanged code needed to verify the effect. Consider shared types,
schemas, API and event contracts, configuration, generated artifacts, migrations,
package exports, version compatibility, and build or deployment boundaries where
they matter. A change confined to one directory can affect another package.

Investigate authorization, data integrity, errors, concurrency, cancellation,
resource lifetime, accessibility, and compatibility in proportion to the affected
behavior.

Be skeptical and play devil's advocate, including with your own conclusions.
Attempt to refute each suspected defect using current code and evidence before
reporting it. Do not invent findings; no confirmed defects is a valid result.
Do not treat a legacy pattern as proof that the same behavior is correct.

Before concluding, revisit the established full or incremental review scope from
complementary angles and make a final search for omissions and combined effects.
Do not limit this pass to revalidating existing findings or defer an investigable
suspicion to a later review. Record any unresolved suspicion as a limitation.

Use observed checks as supporting evidence, not a substitute for tracing behavior.
Run checks only when an already authorized execution surface can verify the pinned
candidate without source or Git mutations; otherwise state that they were not run.

## Re-review the actual delta

Use a reliable prior completed review and its base/head revisions to identify the
effective delta, previous findings to revalidate, and any incomplete coverage.
Account for base changes, rebases, and force-pushes by comparing content; a different
SHA alone does not prove new behavior.

Investigate that delta, its direct and indirect effects, and relevant new evidence.
Do not repeat unrelated completed coverage or insist on findings that have been
fixed or refuted. Without a trustworthy prior baseline, perform a full review and
explain that limitation. If there is no new scope, say so without implying earlier
findings were resolved. Identify a newly discovered pre-existing omission honestly,
not as a regression from the latest commits.

## Report actionable findings

Report introduced or aggravated defects and objective violations of applicable
requirements. Keep unrelated pre-existing defects, taste, and optional improvements
out of the findings. Group manifestations of one root cause and order findings by:

- `[P0]` Critical: immediate action required.
- `[P1]` High: address before merge.
- `[P2]` Medium: relevant defect with bounded impact.
- `[P3]` Low: minor defect, not blocking by itself.

For each finding, use a short bold priority and title, followed by a concise
explanation of the trigger, consequence, evidence, and minimal correction direction.
Link to a tight location at the relevant pinned revision; suggest a focused test
when useful. Use a diagram only when it clarifies the cause or effect.

Identify the reviewed head SHA with a commit link. Keep material limitations
visible, distinguish observed checks from unperformed ones, and avoid repeating
the findings in a summary or narrating the investigation. With no confirmed
findings, state that briefly along with any material limitation; absence of
findings is not a guarantee of correctness.
