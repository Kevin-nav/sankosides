# SankoSlides Frontend

**AI-Powered Presentation Engine for STEM Students**

A Next.js application that powers the SankoSlides platform — an intent-aligned design engine that generates pixel-perfect, academically compliant presentations through conversational AI.

## 🎯 Overview

SankoSlides Frontend provides the user interface for creating AI-generated presentations. Users interact with a conversational "negotiation" phase to define their presentation needs, then watch as slides are generated and quality-checked autonomously through the **Visual Loop** system.

### Key Features

- **Three Generation Modes:**
  - **Replica Engine** — Upload an image, get a matching slide
  - **Synthesis Engine** — Convert PDFs, notes, and docs into presentations
  - **Deep Research Engine** — Generate researched presentations from topics

- **Negotiation Workflow** — Chat-based clarification before generation
- **Visual Loop QA** — Autonomous render → critique → fix pipeline
- **University Profiles** — Persistent branding (logos, colors, citation styles)
- **Real-time Progress** — SSE-powered generation status with agent visibility

## 🛠 Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | Next.js 16 (App Router) |
| UI | React 19 + shadcn/ui + Radix UI |
| Styling | Tailwind CSS 4 |
| Animation | Framer Motion |
| Auth | Firebase (Email + Google OAuth) |
| Database | Neon PostgreSQL + Drizzle ORM |
| State | React Context (AuthProvider) |

## 📁 Project Structure

```
sanko-frontend/
├── app/                    # Next.js App Router pages
│   ├── api/               # API routes (BFF layer)
│   │   ├── auth/          # Auth sync endpoint
│   │   ├── generate/      # Generation API orchestration
│   │   ├── projects/      # Project CRUD
│   │   └── user/          # User management
│   ├── dashboard/         # User dashboard
│   ├── editor/[id]/       # Slide editor workspace
│   ├── playground/        # API testing environment
│   └── (pages)/           # Static pages (about, pricing, etc.)
├── components/
│   ├── dashboard/         # Dashboard UI components
│   ├── editor/            # Editor components (chat, progress, viewer)
│   ├── playground/        # Playground components
│   └── ui/                # shadcn/ui components
├── lib/
│   ├── db/                # Drizzle schema & connection
│   ├── api-client.ts      # Backend API client
│   └── firebase*.ts       # Firebase config
└── types/
    └── generation.ts      # TypeScript types for generation API
```

## 🚀 Getting Started

### Prerequisites

- Node.js 20+
- npm or pnpm
- Firebase project (for authentication)
- Neon PostgreSQL database
- Running [sanko-backend](../sanko-backend) at `localhost:8000`

### Environment Setup

Create a `.env.local` file with:

```env
# Firebase (Client)
NEXT_PUBLIC_FIREBASE_API_KEY=
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=
NEXT_PUBLIC_FIREBASE_PROJECT_ID=
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=
NEXT_PUBLIC_FIREBASE_APP_ID=

# Firebase Admin (Server)
GOOGLE_APPLICATION_CREDENTIALS=./path-to-service-account.json

# Database
DATABASE_URL=postgresql://...

# Backend API
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Installation

```bash
# Install dependencies
npm install

# Run database migrations (if needed)
npx drizzle-kit push

# Start development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the application.

## 📖 Documentation

See the [`docs/`](./docs) folder for detailed documentation:

- [Architecture](./docs/architecture.md) — System design and data flow
- [Components](./docs/components.md) — Component reference
- [API Routes](./docs/api-routes.md) — Frontend API documentation
- [Getting Started](./docs/getting-started.md) — Development setup guide

## 🔗 Related Projects

| Project | Description |
|---------|-------------|
| [sanko-backend](../sanko-backend) | Python FastAPI backend with AI orchestration |
| [sanko-render-service](../sanko-render-service) | Playwright-based slide rendering service |

## 📜 Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Build for production |
| `npm run start` | Start production server |
| `npm run lint` | Run ESLint |
