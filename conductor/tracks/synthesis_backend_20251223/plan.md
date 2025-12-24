# Plan: Synthesis Engine Backend Integration

## Phase 1: Data Models & Schema [checkpoint: 3a272c0]
- [x] Task: Update `app/models/schemas.py` to include `DocumentSection` and `KnowledgeBase` Pydantic models. (c857ce2)
    *   *Details:* Define the structure for holding extracted content.
- [x] Task: Update `FlowState` in `app/crew/flows/slide_generation.py` (and schemas if separated) to include `knowledge_base` field. (f2370a2)
    *   *Details:* Ensure it defaults to `None` and is included in `to_db_dict` / `from_db`.
- [x] Task: Create a unit test `tests/test_schemas_knowledge_base.py` to verify the serialization/deserialization of the new models. (c857ce2)
- [x] Task: Conductor - User Manual Verification 'Data Models & Schema' (Protocol in workflow.md) (3a272c0)

## Phase 2: Synthesis Agent Implementation
- [ ] Task: Create `app/crew/agents/synthesis.py`.
    *   *Details:* Implement `create_synthesis_agent`. Use the `google-genai` logic from the POC (`research/synthesis_poc/pdf_processor.py`) but adapted to output the `KnowledgeBase` structure.
    *   *Note:* Ensure it handles the `GEMINI_API_KEY` from the environment.
- [ ] Task: Create a dedicated test `tests/test_synthesis_agent.py`.
    *   *Details:* Mock the `google.genai.Client` to avoid real API calls during CI. Test that it correctly constructs the `KnowledgeBase` from the mocked response.
- [ ] Task: Conductor - User Manual Verification 'Synthesis Agent Implementation' (Protocol in workflow.md)

## Phase 3: Flow Integration
- [ ] Task: Update `app/crew/flows/slide_generation.py` to add the `run_synthesis` method.
    *   *Details:* This method should accept file inputs (simulated paths for now), run the agent, and update `self.state.knowledge_base`.
- [ ] Task: Update `app/crew/agents/clarifier.py` to accept context.
    *   *Details:* Modify `create_clarification_task` to inject `summary` and `section_titles` into the prompt if `knowledge_base` exists.
- [ ] Task: Conductor - User Manual Verification 'Flow Integration' (Protocol in workflow.md)

## Phase 4: Dynamic Context Tooling (Clarifier)
- [ ] Task: Create a new tool `app/crew/tools/context_tool.py`.
    *   *Details:* Implement `ReadSectionTool` that takes a `section_title` and returns the `content` from `state.knowledge_base`.
- [ ] Task: Register this tool with the `ClarifierAgent` in `app/crew/agents/clarifier.py`.
- [ ] Task: Update `CLARIFIER_SYSTEM_PROMPT` to explicitly instruct the agent on how to use the tool for fact-checking user requests.
- [ ] Task: Conductor - User Manual Verification 'Dynamic Context Tooling' (Protocol in workflow.md)
