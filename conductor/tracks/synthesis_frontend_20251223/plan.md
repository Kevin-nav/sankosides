# Plan: Synthesis Engine - Frontend Integration

## Phase 1: Backend Endpoint Update (FastAPI)
*NOTE: We need to update the backend API endpoint to receive the files first.*
- [ ] Task: Update `sanko-backend/app/api/routers/generation.py` to handle `UploadFile`.
    *   *Details:* Update the `/start` endpoint to accept `multipart/form-data`.
    *   *Logic:* If files are present, call `flow.run_synthesis(files)`.
- [ ] Task: Conductor - User Manual Verification 'Backend Endpoint' (Protocol in workflow.md)

## Phase 2: Frontend API Client & Route
- [ ] Task: Update `sanko-frontend/lib/api-client.ts`.
    *   *Details:* Modify `startGeneration` to support `FormData`.
- [ ] Task: Update `sanko-frontend/app/api/generate/start/route.ts`.
    *   *Details:* Parse `FormData` from the request and forward it to the backend `POST /start` endpoint correctly.
- [ ] Task: Conductor - User Manual Verification 'Frontend API Layer' (Protocol in workflow.md)

## Phase 3: UI Implementation
- [ ] Task: Update `sanko-frontend/components/dashboard/mode-selector.tsx` (or appropriate component).
    *   *Details:* Add a file input/dropzone that appears when `GenerationMode.SYNTHESIS` is active.
- [ ] Task: Update `sanko-frontend/app/dashboard/page.tsx` (or shell) to pass the selected file to the start function.
- [ ] Task: Add "Synthesizing" state to the UI to handle the initial delay.
- [ ] Task: Conductor - User Manual Verification 'UI Implementation' (Protocol in workflow.md)

## Phase 4: End-to-End Verification
- [ ] Task: Perform a full end-to-end test.
    *   *Action:* Upload `Calculus 166.pdf`.
    *   *Verify:* Chat starts, agent knows about "Limits".
- [ ] Task: Conductor - User Manual Verification 'End-to-End' (Protocol in workflow.md)
