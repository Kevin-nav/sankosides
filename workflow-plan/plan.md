# SankoSlides — Developer Handover Specification

> **Document Version:** 1.0  
> **Date:** December 17, 2025  
> **Author:** Kevin Amisom Nchorbuno (Product Architect)  
> **Status:** Ready for Development

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Problem Statement](#2-problem-statement)
3. [Product Vision & Goals](#3-product-vision--goals)
4. [Target Users](#4-target-users)
5. [Core Concepts](#5-core-concepts)
6. [System Architecture](#6-system-architecture)
7. [Feature Specifications](#7-feature-specifications)
8. [API Specifications](#8-api-specifications)
9. [UI/UX Flow](#9-uiux-flow)
10. [Data Models](#10-data-models)
11. [External Integrations](#11-external-integrations)
12. [Edge Cases & Error Handling](#12-edge-cases--error-handling)
13. [Success Criteria](#13-success-criteria)
14. [Technology Stack Summary](#14-technology-stack-summary)
15. [Open Questions for Developers](#15-open-questions-for-developers)

---

## 1. Project Overview

### What is SankoSlides?

**SankoSlides** is a web-based AI-powered slide generation platform that transforms raw academic content (PDFs, lecture notes, images, handwritten equations) into polished, university-compliant PowerPoint presentations. 

Unlike generic design tools (Canva, Beautiful.ai), SankoSlides is purpose-built for **STEM students** who need:
- Complex equation rendering (LaTeX)
- Strict adherence to university formatting guidelines
- Ability to synthesize dense academic material into visual slides

### The Core Innovation

**"One-Shot Generation"** — The system is designed to produce **perfect slides on the first attempt** with zero manual edits required. This is achieved through:

1. **Exhaustive Clarification** — AI asks strategic questions upfront to fully understand intent
2. **Multi-Agent Orchestration** — Specialized AI agents handle different aspects (content, layout, visuals) in parallel
3. **Visual Loop Quality Assurance** — The system self-critiques and fixes rendering issues before delivery

### Why Now?

This project leverages Google's newly released **Interactions API** (December 2025), which provides:
- Server-side conversation memory (no need to resend history)
- Built-in async agents for deep research tasks
- Native Model Context Protocol (MCP) for tool integration

---

## 2. Problem Statement

### The Pain Points

| Pain Point | Description | How SankoSlides Solves It |
|------------|-------------|---------------------------|
| **Time Pressure** | Students spend 3-5 hours creating a 15-slide thesis presentation | Reduce to <10 minutes with One-Shot generation |
| **Formatting Hell** | University templates have strict rules (fonts, margins, logo placement) that are tedious to manually apply | "University Profile" auto-applies rules to every slide |
| **Equation Rendering** | LaTeX equations look pixelated or break in PowerPoint | Server-side SVG generation ensures vector-quality math |
| **Information Overload** | Thesis PDFs have 50+ pages; students don't know what to include | AI synthesizes content, asks clarifying questions, curates key points |
| **Iteration Fatigue** | Generic AI tools require 5-10 rounds of "make it shorter" / "change the color" | Clarification-first approach means fewer iterations |

### The Gap in the Market

| Existing Tool | What It Does | What It Lacks |
|---------------|--------------|---------------|
| **Canva** | General-purpose design | No LaTeX, no academic focus, no AI synthesis |
| **Beautiful.ai** | Smart slide layouts | No document ingestion, no equation support |
| **Gamma.app** | AI slide generation | Generic prompts, no one-shot flow, no university compliance |
| **ChatGPT + Plugins** | Generate content | No visual rendering, no PPTX export, no quality assurance loop |

---

## 3. Product Vision & Goals

### Vision Statement

> "SankoSlides transforms the way students create presentations—from hours of manual work to a single, intelligent conversation."

### Primary Goals (MVP)

| # | Goal | Measurable Target |
|---|------|-------------------|
| 1 | **One-Shot Perfection** | ≥90% of users accept the first generated result without requesting changes |
| 2 | **Academic Compliance** | 100% of slides respect university profile settings (colors, fonts, logo) |
| 3 | **STEM-Ready** | All LaTeX equations render as editable vectors in exported PPTX |
| 4 | **Speed** | Generate a 10-slide deck in <2 minutes end-to-end |
| 5 | **Usability** | A first-time user can complete a generation in <5 interactions |

### Non-Goals (Out of Scope for MVP)

- Real-time collaborative editing (Google Slides-style)
- Mobile app
- Self-hosted/on-premise deployment
- Video generation
- Presenter coaching/rehearsal features

---

## 4. Target Users

### Primary Persona: The Thesis Defender

| Attribute | Description |
|-----------|-------------|
| **Who** | Final-year university student (Engineering, CS, Math, Sciences) |
| **Context** | Preparing for thesis defense or major project presentation |
| **Frustration** | Has 50-page thesis, needs to condense into 12 slides with strict formatting |
| **Goal** | "I want to upload my PDF and get a ready-to-present deck that follows my department's template" |
| **Tech Comfort** | High—comfortable with LaTeX, code, technical tools |

### Secondary Persona: The Group Lead

| Attribute | Description |
|-----------|-------------|
| **Who** | Student assigned to consolidate group project contributions |
| **Context** | Receives 5 different Word docs from teammates, needs unified presentation |
| **Frustration** | Inconsistent formatting, missing citations, repetitive content |
| **Goal** | "I want to upload all files and get one consistent, professional deck" |

### Tertiary Persona: The Last-Minute Crammer

| Attribute | Description |
|-----------|-------------|
| **Who** | Student who procrastinated and needs slides in <1 hour |
| **Context** | Has lecture slides/notes but hasn't organized for presentation |
| **Frustration** | No time to design, just needs something pass-grade |
| **Goal** | "I want to give a topic and get slides fast—even if not perfect" |

---

## 5. Core Concepts

### Concept 1: The Three Engines (Generation Modes)

SankoSlides supports **three distinct generation modes** based on what the user provides as input:

| Mode | Name | Input | What the AI Does |
|------|------|-------|------------------|
| **A** | **Replica Engine** | Image of an existing slide | Vision model maps pixels to CSS. Recreates the slide as editable HTML. |
| **B** | **Synthesis Engine** | PDFs, Word docs, notes, images | Reads content, identifies key points, structures into slide outline, generates visuals. |
| **C** | **Deep Research Engine** | A topic string (e.g., "History of Anansi") | Uses Google's `gemini-deep-research` agent to perform web research, fact-check, and create a structured outline. Runs asynchronously. |

**How Mode is Determined:**
- If user uploads an **image only** → suggest Mode A
- If user uploads **documents** → suggest Mode B  
- If user provides **just a topic** → suggest Mode C
- User can always override the suggestion

---

### Concept 2: The One-Shot Protocol (Clarify → Plan → Execute)

The system **never generates slides immediately**. Instead:

**Step 1: Clarification**
The AI asks 1-3 strategic questions:
- "I see 5 chapters. Should I include all, or focus on specific sections?"
- "What tone: Academic Formal or Conference Engaging?"
- "How many slides are you targeting?"

**Step 2: Contract (Blueprint)**
After clarification, the AI presents a JSON-structured outline:
```
Slide 1: Title — "Machine Learning for Crop Disease Detection"
Slide 2: Overview — Research question, methodology summary
Slide 3: Key Finding 1 — Figure 4: Accuracy comparison chart
Slide 4: Key Finding 2 — Equation: Loss function
...
```

**Step 3: Approval**
User reviews and clicks **"Approve Blueprint"**. Only then does generation begin.

**Why This Matters:**
- Eliminates the "that's not what I wanted" back-and-forth
- Ensures user intent is captured before expensive generation

---

### Concept 3: The Visual Loop (Self-Correcting QA)

Even after content is generated, rendering can have issues (text overflow, wrong colors, broken layouts). The **Visual Loop** catches these:

```
1. Generate HTML for slide → render at 1280×720px
2. Playwright captures screenshot
3. Vision Model compares screenshot to intended design
4. If issues found (e.g., "Title text overflows container"):
   - Fixer Agent modifies CSS
   - Loop back to Step 1
5. Repeat until "Visual Score" > 95%
6. Mark slide as finalized
```

**Key Point:** This loop happens **server-side, invisibly to the user**. User only sees progress updates ("Rendering slide 3... ✓").

---

### Concept 4: University Profile

Users can define a persistent "profile" that automatically applies to all their presentations:

| Field | Example Value | Effect |
|-------|---------------|--------|
| University Name | "University of Ghana" | Displayed on title slide |
| Department | "Department of Computer Science" | Subtitle text |
| Logo URL | `https://...logo.png` | Auto-placed on every slide header |
| Primary Color | `#0056A0` | Headings, accents |
| Secondary Color | `#FFD700` | Highlights |
| Citation Style | "IEEE" | References formatted accordingly |
| Citation Twist | "Bold author names" | Custom modification to standard style |

**Behavior:** If a profile is active, these settings **override** any AI design choices.

---

## 6. System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              USER                                        │
│                     (Browser - Next.js App)                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js 14)                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐    │
│  │ Landing     │  │ Dashboard   │  │ Generator   │  │ Profile      │    │
│  │ Page        │  │ (Projects)  │  │ Workspace   │  │ Settings     │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └──────────────┘    │
│                                                                          │
│  Key Components:                                                         │
│  • SlideStage (1280×720 canvas for preview)                              │
│  • ProgressStream (SSE-based status updates)                             │
│  • BlueprintReview (Contract approval UI)                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ (HTTPS API calls)
┌─────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (FastAPI + Python)                       │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                      CrewAI Orchestrator                          │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │   │
│  │  │Clarifier │ │Content   │ │Layout    │ │Asset     │ │Visual  │  │   │
│  │  │Agent     │ │Synth.    │ │Designer  │ │Generator │ │Critic  │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  Services:                                                               │
│  • InteractionsClient (Google Interactions API)                          │
│  • PlaywrightPool (Headless browser for screenshots)                     │
│  • MathJaxRenderer (LaTeX → SVG)                                         │
│  • PPTXExporter (HTML → .pptx)                                           │
└─────────────────────────────────────────────────────────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────────────────┐
│   Neon (Postgres) │ │  Upstash (Redis) │ │  Cloudflare R2 (Storage)     │
│                    │ │                   │ │                              │
│ • Users            │ │ • Session cache   │ │ • Uploaded PDFs/images       │
│ • Projects         │ │ • Job queue       │ │ • Generated PPTX files       │
│ • Interaction IDs  │ │ • Rate limiting   │ │ • SVG equation assets        │
│ • University       │ │                   │ │ • Generated images           │
│   Profiles         │ │                   │ │                              │
└──────────────────┘ └──────────────────┘ └──────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL SERVICES                                 │
│  • Google Interactions API (Gemini models, Deep Research agent)          │
│  • Nano Banana Pro (Image/diagram generation)                            │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Agent Framework** | CrewAI | Provides structured multi-agent orchestration with agent roles, goals, and parallel execution |
| **AI Backend** | Google Interactions API | Server-side state management reduces latency; built-in async agents for deep research |
| **Rendering** | Server-side Playwright | Consistent rendering environment; no browser variability |
| **Database** | Neon (Postgres) | Serverless, scales to zero, good for MVP |
| **Cache** | Upstash Redis | Serverless Redis for sessions and job queues; no RabbitMQ needed |
| **Storage** | Cloudflare R2 | S3-compatible, cost-effective, good global distribution |
| **No Message Queue** | ❌ RabbitMQ | Overkill for MVP; Upstash Redis queues are sufficient |

---

## 7. Feature Specifications

### Feature 1: User Authentication

| Aspect | Specification |
|--------|---------------|
| **Methods** | Email/password, Google OAuth (both supported) |
| **Session** | JWT stored in httpOnly cookie; refresh via Upstash Redis |
| **Required for** | Saving projects, accessing history, using University Profile |
| **Guest Mode** | Allow anonymous generation (no history saved) — *optional, confirm with team* |

---

### Feature 2: Project Dashboard

| Aspect | Specification |
|--------|---------------|
| **Purpose** | View all past presentations, re-download exports, resume conversations |
| **List View** | Cards showing: Title, creation date, slide count, thumbnail of slide 1 |
| **Actions** | Open, Download PPTX, Delete, Duplicate |
| **Storage** | Project metadata in Neon; PPTX files in Cloudflare R2 |

---

### Feature 3: Generation Workspace

This is the core UI where users interact with the AI.

**Layout:**
- Left panel: Chat interface (conversation with AI)
- Right panel: Slide preview (`SlideStage` component at 1280×720)
- Bottom: Progress bar during generation

**States:**
1. **Idle** — User uploads files or enters topic
2. **Clarifying** — AI is asking questions; user responds
3. **Blueprint Review** — JSON outline displayed; user can approve/edit
4. **Generating** — Progress bar shows status per slide
5. **Complete** — All slides rendered; download button enabled

---

### Feature 4: University Profile Editor

| Field | Input Type | Validation |
|-------|-----------|------------|
| University Name | Text | Required, max 100 chars |
| Department | Text | Optional, max 100 chars |
| Logo | Image upload or URL | Must be PNG/JPEG/SVG, max 2MB |
| Primary Color | Color picker | Hex code |
| Secondary Color | Color picker | Hex code |
| Citation Style | Dropdown | APA, IEEE, Harvard, Chicago, Custom |
| Citation Twist | Text | Optional, free-form instructions |

**Save Behavior:** Stored in Neon, linked to user ID.

---

### Feature 5: STEM Rendering

**Equations:**
- Input: LaTeX syntax wrapped in `$$...$$` OR upload handwritten equation image
- Processing: MathJax (server-side) converts to SVG
- Output: SVG embedded in slide HTML; exported as vector in PPTX

**Diagrams:**
- Input: Mermaid.js syntax in code blocks
- Processing: Mermaid CLI renders to SVG
- Output: SVG embedded in slide

**Code Blocks:**
- Input: Fenced code blocks with language annotation
- Processing: Syntax highlighting via Prism.js or Shiki
- Output: Styled HTML in slide

---

### Feature 6: Deep Research Mode

**Trigger:** User selects "Research" mode and provides a topic.

**Flow:**
1. Backend calls Interactions API with `agent="deep-research-pro-preview"` and `background=true`
2. Immediate response: `{ "id": "int_xxx", "status": "in_progress" }`
3. Backend polls with exponential backoff (10s → 15s → 20s → ... max 60s)
4. Frontend receives progress via SSE: "Searching for sources... ✓", "Reading 12 articles..."
5. On completion, research output is fed to Content Synthesizer Agent
6. Normal One-Shot Protocol continues from there

**Timeout:** If research takes >10 minutes, show user option to cancel or continue waiting.

---

### Feature 7: Export

**Format:** `.pptx` (Microsoft PowerPoint Open XML)

**Library:** `dom-to-pptx` (or similar JS library) for client-side conversion, OR Python `python-pptx` for server-side.

**Requirements:**
- All text boxes must be editable (not images)
- Equations rendered as embedded SVG (vector, scalable)
- Slide size: 1280×720 pixels (standard 16:9)
- Unique `data-id` on every element for future click-to-edit feature

---

## 8. API Specifications

> **Note:** These are high-level specifications. Developers should define exact request/response schemas during implementation.

### Authentication APIs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/auth/register` | POST | Create new user account (email/password) |
| `/api/auth/login` | POST | Authenticate user, return JWT |
| `/api/auth/logout` | POST | Invalidate session |
| `/api/auth/google` | GET | Initiate Google OAuth flow |
| `/api/auth/google/callback` | GET | Handle OAuth callback |
| `/api/auth/me` | GET | Get current user info |

### Project APIs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/projects` | GET | List all user projects |
| `/api/projects` | POST | Create new project |
| `/api/projects/{id}` | GET | Get project details (includes slides) |
| `/api/projects/{id}` | DELETE | Delete project |
| `/api/projects/{id}/download` | GET | Get signed URL for PPTX download |

### Generation APIs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/generate/upload` | POST | Upload files (PDF, images, docs) for processing |
| `/api/generate/clarify` | POST | Send user response to clarification question |
| `/api/generate/blueprint` | GET | Get current blueprint for review |
| `/api/generate/approve` | POST | Approve blueprint and start generation |
| `/api/generate/status` | GET | Get generation progress (SSE stream) |
| `/api/generate/cancel` | POST | Cancel in-progress generation |

### Profile APIs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/profile/university` | GET | Get user's university profile |
| `/api/profile/university` | PUT | Update university profile |
| `/api/profile/university/logo` | POST | Upload logo image |

---

## 9. UI/UX Flow

### Flow 1: New User First Generation

```
1. User lands on homepage → sees value proposition
2. Clicks "Get Started" → redirected to login/signup
3. After auth → lands on empty dashboard ("No projects yet")
4. Clicks "New Presentation" → enters Generator Workspace
5. System prompts: "Upload files or describe your topic"
6. User uploads thesis PDF
7. System detects Mode B (Synthesis) → asks clarification questions
8. User answers 2-3 questions
9. System shows Blueprint → user reviews slide outline
10. User clicks "Approve"
11. Progress bar shows generation status
12. All slides complete → preview shown
13. User clicks "Download PPTX"
14. Project saved to dashboard for future access
```

### Flow 2: Returning User

```
1. User logs in → sees dashboard with past projects
2. Clicks on existing project → sees slides
3. Can download again or start new project
```

### Flow 3: Deep Research Mode

```
1. User clicks "New Presentation"
2. Instead of uploading, types topic: "Renewable energy policy in West Africa"
3. System suggests Mode C (Deep Research)
4. User confirms → research agent starts (async)
5. Progress updates: "Searching sources... Reading articles..."
6. ~30 seconds later: research complete
7. Clarifier asks: "I found info on solar, wind, and hydro. Focus on all or specific?"
8. Normal flow continues from clarification
```

---

## 10. Data Models

> **Note:** These are conceptual models. Developers should define exact SQL schemas.

### User
```
- id: UUID
- email: string (unique)
- password_hash: string (nullable if OAuth-only)
- auth_provider: enum (email, google)
- created_at: timestamp
- updated_at: timestamp
```

### UniversityProfile
```
- id: UUID
- user_id: FK → User
- university_name: string
- department: string (nullable)
- logo_url: string (nullable)
- primary_color: string (hex)
- secondary_color: string (hex)
- citation_style: enum (APA, IEEE, Harvard, Chicago, Custom)
- citation_twist: string (nullable)
```

### Project
```
- id: UUID
- user_id: FK → User
- title: string
- mode: enum (replica, synthesis, research)
- interaction_id: string (Google Interactions API ID)
- status: enum (draft, generating, completed, failed)
- pptx_url: string (nullable, Cloudflare R2 URL)
- created_at: timestamp
- updated_at: timestamp
```

### Slide
```
- id: UUID
- project_id: FK → Project
- order: integer
- title: string
- html_content: text
- thumbnail_url: string (nullable)
```

---

## 11. External Integrations

### Google Interactions API

**Purpose:** Core AI backbone for conversation, content generation, and research.

**Key Concepts:**
- `store=true` keeps conversation history server-side
- `previous_interaction_id` links multi-turn conversations
- `background=true` for async Deep Research agent

**Python SDK:** `google-genai`

**Example:**
```python
from google import genai

client = genai.Client(api_key=API_KEY)

# First turn
interaction = client.interactions.create(
    model="gemini-3-pro-preview",
    input="Analyze this PDF for key presentation points",
    config={"store": True}
)

# Follow-up turn
response = client.interactions.create(
    model="gemini-3-pro-preview",
    input="Focus on the Results section",
    previous_interaction_id=interaction.id,
    config={"store": True}
)
```

Refer to: [Interactions API Technical Guide Research.md](./Interactions%20API%20Technical%20Guide%20Research.md)

---

### Nano Banana Pro

**Purpose:** AI image generation for diagrams, illustrations, and visual content.

**Usage:** When the Content Synthesizer determines a slide needs a custom image (e.g., "conceptual diagram of neural network"), the Asset Generator calls Nano Banana Pro.

**Integration:** *Developers to obtain API documentation and implement client.*

---

### Cloudflare R2

**Purpose:** Object storage for user uploads and generated files.

**SDK:** `boto3` (S3-compatible) or Cloudflare's official SDK.

**Buckets:**
- `sanko-uploads` — user-uploaded PDFs, images
- `sanko-exports` — generated PPTX files
- `sanko-assets` — SVG equations, generated images

---

### Neon (PostgreSQL)

**Purpose:** Primary relational database.

**Connection:** Standard PostgreSQL driver (`asyncpg` for Python).

**Features to use:**
- Connection pooling (built-in)
- Branching (for dev/staging environments)

---

### Upstash Redis

**Purpose:** Caching, sessions, and job queues.

**SDK:** `upstash-redis` (REST-based, serverless-friendly).

**Usage:**
- Session tokens: `session:{user_id}` → JWT
- Generation jobs: Redis Streams or simple queue
- Rate limiting: Token bucket per user

---

## 12. Edge Cases & Error Handling

| Scenario | Expected Behavior |
|----------|-------------------|
| **User uploads corrupted PDF** | Show error: "We couldn't read this file. Please try a different PDF." |
| **LaTeX syntax is invalid** | Render placeholder: "[Equation Error: Please check syntax]" and highlight in red |
| **Deep Research takes >10 min** | Show "Still researching... [Continue Waiting] [Try a narrower topic]" |
| **Visual Loop fails after 5 iterations** | Accept current state with warning: "Some slides may need manual adjustment" |
| **User loses connection mid-generation** | Generation continues server-side; user can refresh to see progress |
| **Interactions API rate limit** | Queue requests; show "High demand, please wait..." |
| **PPTX export fails** | Retry once; if still fails, offer HTML download as fallback |
| **Empty slide content** | AI detects this and asks: "I don't have enough content for Slide 4. Can you provide more details?" |

---

## 13. Success Criteria

### Quantitative Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **One-Shot Rate** | ≥90% | % of users who download without requesting changes |
| **Average Clarification Turns** | ≤3 | Count of AI questions before blueprint approval |
| **End-to-End Latency** | <2 min for 10 slides | Time from "Approve" to "Complete" |
| **Visual Loop Iterations** | ≤2 per slide | Internal metric; log and aggregate |
| **PPTX Compatibility** | 100% | Manual test: open in PowerPoint, all elements editable |
| **User Retention** | ≥30% return within 30 days | Analytics tracking |

### Qualitative Goals

- Users describe the experience as "magical" or "effortless"
- The interface feels **simple and approachable** (not overwhelming)
- STEM students recommend it to classmates

---

## 14. Technology Stack Summary

| Layer | Technology | Notes |
|-------|------------|-------|
| **Frontend** | Next.js 14, React, Tailwind CSS | App Router, SSR for SEO |
| **Backend** | Python, FastAPI | Async, type-safe |
| **AI Orchestration** | CrewAI | Multi-agent framework |
| **AI Models** | Google Gemini (via Interactions API) | gemini-3-pro, deep-research agent |
| **Image Generation** | Nano Banana Pro | Custom diagrams |
| **Equation Rendering** | MathJax (Node.js) | LaTeX → SVG |
| **Diagram Rendering** | Mermaid CLI | Mermaid → SVG |
| **Browser Automation** | Playwright (Python) | Screenshot capture |
| **Database** | Neon (PostgreSQL) | Serverless |
| **Cache/Queue** | Upstash Redis | Serverless |
| **Object Storage** | Cloudflare R2 | S3-compatible |
| **Hosting (Frontend)** | Vercel | Integrated with Next.js |
| **Hosting (Backend)** | Fly.io / Railway / Render | Python hosting |

---

## 15. Open Questions for Developers

> These are decisions that require developer input during implementation.

1. **Authentication:** Should we support guest/anonymous mode where users can generate without signing up?

2. **Export Library:** Server-side (`python-pptx`) vs client-side (`dom-to-pptx`)? Trade-offs?

3. **MathJax Integration:** Run MathJax as a subprocess, or use a dedicated Node.js microservice?

4. **Playwright Pool:** How many browser instances to maintain? Auto-scaling strategy?

5. **Error Recovery:** If generation fails mid-way, can we resume, or must we restart?

6. **Image Caching:** Cache Nano Banana Pro outputs in R2 with content-hash keys to avoid regenerating identical images?

7. **Rate Limits:** What limits per user? Per IP? How to handle abuse?

---

## Appendix: Reference Documents

- [idea.md](./idea.md) — Original Product Requirements Document
- [Interactions API Technical Guide Research.md](./Interactions%20API%20Technical%20Guide%20Research.md) — Detailed API documentation

---

*This document provides sufficient context for developers to begin implementation. For questions, contact the Product Architect.*
