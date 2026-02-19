# Slide Element Tree Rollout Guide

## Scope

This rollout introduces a structured `element_tree` rendering pipeline while preserving legacy HTML rendering as the default fallback.

Convex remains the only database in this architecture. No SQL or secondary datastore is introduced by this rollout.

## Feature Flags

All flags live in `sanko-backend/app/core/config.py`:

- `enable_element_tree_pipeline`
  - Enables generation-time element-tree materialization and HTML rendering from the tree.
  - Disabled: generation uses legacy DB/Jinja template HTML path.
- `enable_element_tree_canvas`
  - Reserved for frontend canvas exposure controls.
  - Disabled: clients should continue iframe/legacy rendering behavior.
  - Frontend gate uses `NEXT_PUBLIC_ENABLE_ELEMENT_TREE_CANVAS=true`.
- `enable_element_tree_export`
  - Enables PPTX/PDF exporters to prefer `element_tree` coordinates.
  - Disabled: exporters use legacy export logic even if `element_tree` is present.

## Rollout Sequence

1. Deploy with all three flags `false`.
2. Enable `enable_element_tree_pipeline=true` in staging and validate generation behavior.
3. Enable `enable_element_tree_canvas=true` for internal users and validate edit/save flow.
4. Enable `enable_element_tree_export=true` and compare PPTX/PDF against baseline sample decks.
5. Roll out to production cohorts gradually.

## Rollback

If regressions appear:

1. Set all flags to `false`.
2. Regenerate slides as needed through the legacy HTML/template path.
3. Continue serving existing sessions; legacy fallback remains intact.

## Validation Checklist

- Legacy generation path still produces non-empty `rendered_html` when pipeline flag is disabled.
- Element-tree generation path works when pipeline flag is enabled.
- PDF and PPTX export behavior follows `enable_element_tree_export`.
- Convex project/session updates remain unchanged and operational.
