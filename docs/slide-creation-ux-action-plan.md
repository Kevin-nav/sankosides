# Slide Creation UX Action Plan

This document captures the agreed work for improving the slide creation flow (clarify -> blueprint -> generate -> viewer), so we can execute it in follow-up PR updates without losing scope.

## Goals

- Make the editor flow resilient, resumable, and clear at every step.
- Eliminate dead-end states and misleading controls.
- Align frontend/backend contracts so wizard and generation behave predictably.
- Improve user trust through accurate progress, explicit errors, and recovery actions.

## Priority Checklist

## P0 - Reliability and State Integrity

- [ ] Fix generation error handling so failed runs do **not** transition to completed viewer state.
- [ ] Add a proper generation failure UI state (error details + retry path + back to blueprint).
- [ ] Make editor sessions resumable:
  - Persist/restore `sessionId`
  - Restore stage from project/session status
  - Avoid always resetting to clarifier on reopen.
- [ ] Ensure project/session state is synced consistently between frontend and Convex/backend.

## P1 - API Contract Alignment

- [ ] Align `/api/generate/start` contract with wizard needs (sections/next-step data, or remove assumptions from UI).
- [ ] Align clarify streaming payload so `field_key`, options, and question metadata are real (not fabricated fallbacks).
- [ ] Ensure section-selection flow is deterministic for PDF mode.
- [ ] Add contract-safe fallback behavior when backend omits optional fields.

## P1 - Core UX Flow Improvements

- [ ] Add explicit Back/Edit controls in wizard phases.
- [ ] Add clear Retry/Cancel actions for failed async steps (start, clarify, confirm, approve, generate).
- [ ] Prevent double-submit on key actions (approve, generate, confirm) with loading/disabled state.
- [ ] Ensure every async operation has visible status: idle, loading, success, error.

## P2 - Trust and Clarity

- [ ] Remove or wire dead top-bar actions (Share/Export). Do not show non-functional controls.
- [ ] Replace synthetic/hardcoded progress values with real backend data, or explicitly label as estimate.
- [ ] Improve file upload clarity:
  - Unsupported file types should show explicit feedback (not silent skip).
  - Failed uploads should state whether generation will continue without that file.
  - Continue button logic should be explicit about what files are included/excluded.

## P2 - Blueprint and Slide Viewer UX

- [ ] Improve blueprint approval feedback (inline error/toast, loading state, recovery actions).
- [ ] Ensure blueprint editing interactions remain stable after reorder/add/remove.
- [ ] Ensure viewer clearly handles empty/no-slides and fetch failures with actionable next steps.

## P3 - Layout and Accessibility Polish

- [ ] Improve editor responsiveness for smaller screens (sidebar/canvas balance).
- [ ] Verify keyboard and focus behavior across wizard, blueprint, and viewer actions.
- [ ] Clean up inconsistent copy and any text encoding artifacts in user-facing UI.

## Definition of Done

- [ ] User can leave and reopen an in-progress project and land in the correct stage.
- [ ] Failed generation is recoverable without manual session guessing.
- [ ] Wizard + backend data exchange is schema-consistent and testable.
- [ ] No visible dead controls in primary editor shell.
- [ ] Each stage has clear loading, error, and retry behavior.

## Suggested Execution Order

1. P0 reliability/state fixes
2. API contract alignment
3. Wizard/back-edit/retry UX
4. Blueprint + viewer error/recovery polish
5. Responsiveness and accessibility cleanup

## PR Follow-up Tracking

- [ ] Address reviewer comments on current PR
- [ ] Apply remaining P0/P1 items not yet merged
- [ ] Re-test full end-to-end flow (new project, reopen, failure path, successful generation)
