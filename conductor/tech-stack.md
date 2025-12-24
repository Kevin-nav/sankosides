# Technology Stack: SankoSlides

## Backend (Orchestration & AI)
*   **Framework:** FastAPI (Python 3.11+)
*   **Orchestration:** CrewAI (Multi-agent flows with SSE streaming)
*   **LLM:** Google Gemini (Gemini 3 Flash for multimodal synthesis, Pro for reasoning)
*   **Task Management:** Event-driven pipeline with user review "pause points."
*   **Testing:** Pytest

## Frontend (User Interface)
*   **Framework:** Next.js 16 (App Router, React 19)
*   **Styling:** Tailwind CSS 4 & Framer Motion
*   **Components:** shadcn/ui & Radix UI
*   **State Management:** React Context (Auth)
*   **ORM:** Drizzle ORM

## Infrastructure & Persistence
*   **Database:** Neon PostgreSQL
*   **Authentication:** Firebase (Email + Google OAuth)
*   **Migrations:** Alembic (Backend) & Drizzle Kit (Frontend)
*   **API Communication:** REST & SSE (Server-Sent Events)

## Rendering Service (Deterministic Output)
*   **Framework:** Node.js
*   **Core Tool:** Playwright (for high-fidelity SVG/HTML capture)
*   **STEM Features:** LaTeX (MathJax/KaTeX), Mermaid.js (Diagrams), Citation formatting (IEEE/APA)
*   **Architecture:** Stateless microservice for vector-quality math and code.
