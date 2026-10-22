---
name: implement-design
description: Implement or review an established interface design using existing repository components. Use for UI work guided by specifications, Figma, or the product's existing screens and conventions.
---

# Implement an established design

Steward implements and verifies the interface in the same task. Follow the
established design and the repository's components, tokens, and conventions.

## Understand the intended behavior

Read the applicable repository guidance and inspect the existing implementation.
Identify the user goal, relevant flow, and required states, including loading,
empty, error, success, and disabled states where applicable. Preserve product
semantics and distinguish supplied requirements from unresolved decisions.

## Follow the design source

Reuse existing components and interaction patterns before introducing a new
variation. Preserve visual hierarchy, spacing, typography, content, and responsive
behavior. Check semantic structure, keyboard interaction, focus, and accessible
names for the changed interface.

When an exact design source is relevant, inspect it with the available tools
before claiming measurements, variants, tokens, assets, or interactions from it.
For Figma, identify the exact file and nodes, then inspect the relevant hierarchy,
variants, layout constraints, sizing, typography, colors, effects, tokens, assets,
and interactions. Retain the source reference and a concise record of inspected
facts and unresolved details, keeping broad raw output out of the report.

Use screenshots as evidence for visible appearance; do not claim they establish
uninspected source properties. Compare only states and viewports supported by
the source. Verify runtime behavior, product semantics, and accessibility with
their own implementation or requirements evidence; the design source alone does
not prove them. Keep external design files unchanged unless the user requests
an edit.

If required source data is unavailable or contradicts the repository, report
the specific gap or conflict. Ask for a decision only when it materially affects
correct implementation; continue independent work supported by current evidence.

## Verify the implementation

Inspect the rendered result against the relevant source at the affected states
and viewports. Use available checks and state any rendering or interaction
verification that could not be performed. Report material deviations and
unresolved decisions without presenting them as accepted design changes.
