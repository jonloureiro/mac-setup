---
name: source-verification
description: Verify tool, API, dependency, configuration, or workflow behavior when a decision depends on the current version or a material unverified assumption.
---

# Source verification

## Identify the question

State the specific behavior that affects the task and what evidence would resolve
it. Identify the relevant version, revision, environment, or permissions. Keep the
investigation bounded to the decision it needs to support.

## Inspect the evidence

Start with relevant current evidence: source, installed versions, implementation,
type definitions, and read-only tool output. Use memory, summaries, and search
snippets as leads; inspect the underlying source before relying on a material
technical claim. A screenshot supports visible appearance, not uninspected code
or API behavior.

Check official documentation, specifications, release notes, or versioned upstream
source when the local evidence is incomplete or the claim requires current
external authority. Match the source to the version in use and retain its link,
revision, or retrieval date where relevant. Describe material differences between
documented and observed behavior.

## Test only what remains uncertain

When an experiment would resolve a material uncertainty, run the smallest useful
check. Prefer read-only operations; isolate required writes in a disposable target
within the task's permissions. Include a negative case when false acceptance
could cause a consequential mistake. Observe the result and exit status rather
than treating a command's invocation as proof of success.

If an experiment escapes its disposable target, stop the experiment, inspect the
affected state, and undo only its proven writes while preserving pre-existing or
concurrent work. Verify restoration and report any unresolved effect.

## Use the conclusion within its limits

Distinguish verified facts, inferences, and unknowns. Do not claim stronger support
than the inspected evidence provides. Report the result, its material caveat, and
the source or re-check command in proportion to the task.

If a required source is unavailable or evidence conflicts without a clear
resolution, leave the assumption unresolved and pause only the work that depends
on it. Continue independent work supported by evidence. If later evidence changes
the conclusion, reassess and correct the dependent changes within the authorized
scope. Keep credentials and private payloads out of reports and retained evidence.
