---
name: owner-publication
description: Prepare commit proposals and pull-request descriptions for manual publication, when requested or after completing a coherent implementation batch.
---

# Owner publication

Prepare publication text from the current change. The human owner performs branch
and worktree mutations, staging, commits, pushes, PR creation or merge, releases,
and remote-ref changes. The global Steward instructions define the sole commit
exception: an explicitly requested local branch update by merge, including its
necessary staging and merge commit with Git's generated default message unchanged.
This skill does not grant Git-write or publication authority.

## Inspect the current change

Read the relevant diff, repository instructions, publication templates, and
verification results. Inspect accepted examples when needed to resolve unclear
conventions. Separate the current task's changes from unrelated working-tree
changes and identify the candidate the proposal describes.

Rewrite proposals when the scope or implementation changes so they describe the
current result. Retain only decisions and trade-offs that help the reviewer assess
it. Distinguish observed checks and actions from reported, skipped, or unknown ones;
bind claims to the relevant diff, SHA, or workflow run when available.

## Prepare the text

After a coherent authorized batch is complete, present one English Conventional
Commit proposal without waiting for a separate request. Use an imperative summary
such as `fix(scope): describe the corrected behavior`, unless repository guidance
requires a different convention. Cover only the completed batch and avoid repeating
the proposal on ordinary conversational turns.

For an authorized merge update, keep the default merge message. Do not replace it
with a Conventional Commit proposal or suggest amending the completed merge.

Keep the PR title and description aligned with the current diff and repository
template, structure, and language; default to English when no convention exists.
Lead with the concrete problem and resulting behavior. Include relevant validation
and material limitations; add trade-offs, risks, or rollback information when they
help the reviewer. Scale detail to the change.

## Retain an ongoing draft when useful

For ongoing work that needs a durable draft, use one private file at
`${XDG_STATE_HOME:-$HOME/.local/state}/codex/work/<repository-id>/<work-id>/publication.md`.
Use a repository identifier that distinguishes unrelated repositories with the same
name, and a stable task-specific work identifier. Reuse that task's file and never
overwrite another task's draft.

Keep private directories at mode `0700` and the draft at `0600`. Rewrite the current
proposal instead of appending a journal. Keep the file focused on publication text,
without using it as chat history or an ongoing work log. Include only sections with
useful current information and report the path when saving it. Keep secrets and
private payloads out of the draft.

A small one-off text request can be answered directly in chat. If private storage
is unavailable within the active permissions, provide the text in chat and state
that it was not saved. Do not modify repository ignore files or Git metadata just
to store drafts, and do not mutate Git or GitHub to publish them.
