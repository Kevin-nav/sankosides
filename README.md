# SankoSlides (Monorepo)

**AI-Powered Presentation Engine for STEM Students**

SankoSlides is an intent-aligned design engine that generates pixel-perfect, academically compliant presentations through conversational AI. It uses a multi-agent orchestration pipeline to handle everything from research and content synthesis to visual quality assurance.

## 🚀 Project Overview

SankoSlides helps students and researchers convert complex STEM topics, PDFs, and notes into professional slide decks. Unlike generic AI generators, SankoSlides focuses on **academic compliance**, **visual accuracy (STEM-focused)**, and **intent alignment** through a human-in-the-loop negotiation phase.

### Core Engines
- **Replica Engine**: Transform images/sketches into matching slides.
- **Synthesis Engine**: Convert PDFs, notes, and documents into structured presentations.
- **Deep Research Engine**: Generate comprehensive, researched decks from a simple topic.

---

## 🏗 Repository Structure

This is a monorepo containing all components of the SankoSlides ecosystem:

| Directory | Component | Technology | Description |
|-----------|-----------|------------|-------------|
| [`/sanko-frontend`](./sanko-frontend) | **Frontend** | Next.js, Tailwind, Shadcn | Modern web dashboard and interactive editor. |
| [`/sanko-backend`](./sanko-backend) | **Backend** | Python, FastAPI, CrewAI | Multi-agent orchestration and API logic. |
| [`/sanko-render-service`](./sanko-render-service) | **Render Service** | Node.js, Playwright | Renders HTML/CSS/LaTeX slides into visual assets. |

---

## 🛠 System Architecture

SankoSlides uses a sophisticated multi-agent pipeline powered by **Google Gemini** and orchestrated by **CrewAI**:

1.  **Negotiation (Clarifier Agent)**: Resolves ambiguity in user requests before generation starts.
2.  **Synthesis (Planner & Generator Agents)**: Processes input data and maps content to semantic HTML templates.
3.  **Visual Loop (QA Agent & Helper Agent)**: Autonomous loop that renders slides, critiques them for visual bugs, and applies fixes.

---

## 🚦 Getting Started

### 1. Prerequisites
- **Python 3.11+**
- **Node.js 20+**
- **Google Gemini API Key**
- **PostgreSQL** (Neon or local)
- **Firebase Project** (for Auth)

### 2. Installation & Setup

#### Backend Setup
```bash
cd sanko-backend
python -m venv venv
./venv/Scripts/activate # Windows
pip install -r requirements.txt
cp .env.example .env # Add your Gemini API Key
python run.py
```

#### Render Service Setup
```bash
cd sanko-render-service
npm install
node server.js
```

#### Frontend Setup
```bash
cd sanko-frontend
npm install
# Configure .env.local with Firebase/Database/Backend URLs
npm run dev
```

---

## 📖 Documentation

Detailed documentation for each service can be found in their respective directories:
- [Backend Documentation](./sanko-backend/docs/)
- [Frontend Documentation](./sanko-frontend/docs/)

---

## 📜 License

MIT License - see individual directories for details.
