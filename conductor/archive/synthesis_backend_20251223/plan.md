# Plan: Synthesis Engine Backend Integration

## Phase 1: Data Models & Schema [checkpoint: 3a272c0]
- [x] Task: Update `app/models/schemas.py` to include `DocumentSection` and `KnowledgeBase` Pydantic models. (c857ce2)
    *   *Details:* Define the structure for holding extracted content.
- [x] Task: Update `FlowState` in `app/crew/flows/slide_generation.py` (and schemas if separated) to include `knowledge_base` field. (f2370a2)
    *   *Details:* Ensure it defaults to `None` and is included in `to_db_dict` / `from_db`.
- [x] Task: Create a unit test `tests/test_schemas_knowledge_base.py` to verify the serialization/deserialization of the new models. (c857ce2)
- [x] Task: Conductor - User Manual Verification 'Data Models & Schema' (Protocol in workflow.md) (3a272c0)

## Phase 2: Synthesis Tool Implementation
- [x] Task: Create `app/crew/tools/synthesis_tool.py`.
    *   *Details:* Implemented `SynthesisTool` using `google-genai` logic from the POC, adapted to output the structured `KnowledgeBase`.
    *   *Note:* Uses `crewai.tools.BaseTool` for proper integration.
- [x] Task: Create a dedicated test `tests/test_synthesis_tool.py`.
    *   *Details:* Verified the tool correctly constructs the `KnowledgeBase` from mocked Gemini responses.
- [x] Task: Conductor - User Manual Verification 'Synthesis Tool Implementation' (Protocol in workflow.md) (checkpoint: manual)

## Phase 3: Flow Integration
- [x] Task: Update `app/crew/flows/slide_generation.py` to add the `run_synthesis` method. (09f196b)
    *   *Details:* This method should accept file inputs (simulated paths for now), run the agent, and update `self.state.knowledge_base`.
- [x] Task: Update `app/crew/agents/clarifier.py` to accept context. (2e07943)
    *   *Details:* Modify `create_clarification_task` to inject `summary` and `section_titles` into the prompt if `knowledge_base` exists.
- [x] Task: Conductor - User Manual Verification 'Flow Integration' (Protocol in workflow.md) (manual)

## Phase 4: Dynamic Context Tooling (Clarifier)
- [x] Task: Create a new tool `app/crew/tools/context_tool.py`. (869e351)
    *   *Details:* Implement `ReadSectionTool` that takes a `section_title` and returns the `content` from `state.knowledge_base`.
- [x] Task: Register this tool with the `ClarifierAgent` in `app/crew/agents/clarifier.py`. (2e07943)
- [x] Task: Update `CLARIFIER_SYSTEM_PROMPT` to explicitly instruct the agent on how to use the tool for fact-checking user requests. (2e07943)
- [x] Task: Conductor - User Manual Verification 'Dynamic Context Tooling' (Protocol in workflow.md) (manual)
