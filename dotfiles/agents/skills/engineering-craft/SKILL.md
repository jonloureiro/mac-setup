---
name: engineering-craft
description: Implement, debug, refactor, or review code with clear ownership, readable control flow, and the smallest complete solution within the requested outcome.
---

# Engineering craft

## Find the behavior's owner

Read the applicable repository guidance and trace the relevant entry point,
callers, domain decisions, state, external boundaries, and outcome. Include failure,
cancellation, concurrency, and resource lifetime where they affect the change.

For a defect, reproduce the reported behavior when possible and repair its real
owner rather than repeating guards at each symptom. Keep the repair within the
requested outcome and record unrelated findings separately.

Place changes where a maintainer would look for that behavior. Keep code together
when it changes for the same reason; split for a real ownership, lifecycle, runtime,
trust, or dependency boundary. Make the dependency direction clear.

## Reduce before adding

Prefer, in order: leave unneeded behavior unbuilt; delete obsolete code; repair
the existing design locally; reuse repository patterns; use the standard library
or native platform behavior; reuse an accepted dependency; then add the minimum
implementation still required.

Every new abstraction, dependency, file, or layer needs a current consumer and a
reason the simpler options do not suffice. Optimize for the maintainer's cognitive
load, keeping enough structure to make responsibilities clear.

## Make the code locally readable

- Use names that reveal intent and functions with one coherent responsibility.
- Prefer early returns and guard clauses so the normal path remains easy to follow.
- Give each condition one readable decision. Separate independent rejection reasons
  instead of mixing them into long Boolean expressions; use a named predicate for
  a cohesive domain invariant without hiding a formula that needs separate guards.
- Keep dependencies, state transitions, errors, and resource ownership visible.
- Prefer a named helper over an inline self-invoking routine. Follow one consistent
  pattern in the edited area unless a material difference justifies another form.
- Use types to expose invariants. Improve placement, names, types, and flow before
  adding comments; use comments for durable rationale and external constraints.

Preserve exhaustive state handling, cleanup, error propagation, transactions,
cancellation, concurrency correctness, authorization, privacy, accessibility, and
data-loss protection while simplifying control flow.

## Prove the changed behavior

Use the repository's existing verification architecture. Start with focused,
deterministic checks and broaden according to the affected behavior and remaining
uncertainty. For a regression, show the failure before and success after the repair
when practical.

Add behavioral coverage when the change or risk warrants it. Tests should be
isolated, order-independent, independently runnable, and safe to run in parallel;
avoid tests that merely repeat implementation details or exercise trivial getters.
Do not weaken accepted behavior or protections to make a check pass. Investigate
failures and distinguish observed results from checks that were skipped or could
not run.

## Review the result

Inspect the final diff for misplaced responsibilities, unnecessary machinery,
unclear control flow, missing behavior, and changes outside the requested outcome.
Report what changed, the relevant verification, and any material limitations.
