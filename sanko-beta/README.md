# SankoSlides Beta Landing Page

> Documentation for developers and AI agents working on the beta landing page project.

---

## What is SankoSlides?

**SankoSlides** is an AI-powered presentation engine built specifically for **STEM university students**. Unlike generic AI slide generators, SankoSlides focuses on:

1. **Academic Compliance** — Proper referencing (APA, Harvard, IEEE), British English, SI units
2. **Visual Accuracy** — LaTeX equations, Mermaid diagrams, properly formatted citations
3. **Intent Alignment** — A conversational AI that clarifies requirements before generating

### The Core Engines

| Engine | Purpose | Input → Output |
|--------|---------|----------------|
| **Replica** | Recreate existing slides | Image/sketch → Editable slide |
| **Synthesis** | Extract from documents | PDFs/notes → Structured presentation |
| **Deep Research** | Research and create | Topic → Researched slide deck |

### Tech Stack Overview

| Component | Technology | Location |
|-----------|------------|----------|
| Frontend (Main App) | Next.js, Tailwind, Shadcn | `/sanko-frontend` |
| Backend | Python, FastAPI, CrewAI | `/sanko-backend` |
| Render Service | Node.js, Playwright | `/sanko-render-service` |
| **Beta Landing Page** | React, Vite, GSAP | `/sanko-beta` |

---

## The Beta Landing Page

### Purpose

The beta landing page (`/sanko-beta`) is a **standalone marketing site** to collect early beta testers, primarily from **Ghanaian universities** with a focus on **University of Mines and Technology (UMaT)**.

### Target Audience

- University students in Ghana (Levels 100-400, Masters, PhD)
- Students who frequently create academic presentations
- Primary focus: UMaT students (Tarkwa and Essikado campuses)

### Goals

1. **Collect signups** with rich user data for product insights
2. **Build anticipation** before public launch
3. **Validate messaging** that resonates with Ghanaian students

---

## Project Structure

```
sanko-beta/
├── src/
│   ├── components/
│   │   ├── Hero.tsx              # Main hero with headline & CTA
│   │   ├── ProblemSection.tsx    # "Sound Familiar?" pain points
│   │   ├── FeaturesSection.tsx   # 6 feature cards
│   │   ├── HowItWorks.tsx        # 3-step process
│   │   ├── FAQSection.tsx        # Accordion FAQs
│   │   ├── Navbar.tsx            # Sticky navigation
│   │   ├── Footer.tsx            # Links & social
│   │   └── BetaSignupForm.tsx    # Multi-step modal form
│   ├── data/
│   │   └── constants.ts          # Universities, form options, FAQs
│   ├── App.tsx                   # Main app composing all sections
│   ├── main.tsx                  # Entry point
│   └── index.css                 # Tailwind + design system
├── public/
│   └── favicon.svg
├── index.html                    # SEO meta tags, fonts
├── vite.config.ts
├── package.json
└── tsconfig.json
```

---

## Design System

### Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--color-primary` | `#10b981` (Emerald) | CTAs, accents, highlights |
| `--color-primary-dark` | `#059669` | Hover states |
| `--color-bg-dark` | `#0a0a0a` | Page background |
| `--color-bg-card` | `#171717` | Card backgrounds |
| `--color-text-primary` | `#fafafa` | Main text |
| `--color-text-secondary` | `#a3a3a3` | Muted text |

### Typography

- **Font**: Inter (from Google Fonts)
- **Headings**: Font-weight 700-800, tight tracking
- **Body**: Font-weight 400, 1.6 line-height

### Design Principles

1. **Mobile-first** — 50%+ of users expected on mobile
2. **No gradients** — Clean, solid colors (per user feedback)
3. **Animations on mobile** — GSAP/Framer work on touch devices
4. **Dark mode only** — Matches the main app aesthetic

---

## Key Components

### Hero (`Hero.tsx`)

**Purpose**: First impression, main CTA

**Key elements**:
- Badge: "Now accepting beta testers"
- Headline: "It's 11 PM. Your Presentation is Tomorrow. We've Got You."
- Subheadline: Value prop in one sentence
- CTA button: Opens signup form
- Social proof: "Limited spots for UMaT students"

**Animations**: GSAP timeline with staggered fade-in on load

---

### BetaSignupForm (`BetaSignupForm.tsx`)

**Purpose**: Collect beta tester information

**Steps**:
1. **Contact**: Full name, email, WhatsApp (optional)
2. **Academic Profile**: University, campus (for UMaT), academic level, department
3. **Insights**: Presentation frequency, current tools, pain points, expectations, referral source

**Key behaviors**:
- Conditional campus dropdown (only for UMaT)
- Validation before proceeding
- Framer Motion slide transitions between steps
- Success state with confetti-like animation
- Currently saves to localStorage (needs API integration)

---

### Constants (`data/constants.ts`)

Contains all form options:

```typescript
// Universities (UMaT is primary, has campus selection)
universities: [
  { id: "umat", name: "University of Mines and Technology (UMaT)", 
    hasCampuses: true, campuses: ["Tarkwa Campus (Main)", "Essikado Campus"] },
  { id: "knust", name: "Kwame Nkrumah University of Science and Technology (KNUST)" },
  { id: "ucc", name: "University of Cape Coast (UCC)" },
  // ... 8 more
]

// Academic levels with Ghana-specific terminology
academicLevels: [
  { id: "100", label: "Level 100 (Freshman)" },
  { id: "200", label: "Level 200 (Sophomore)" },
  // ... through Level 400, Masters, PhD, Lecturer
]
```

---

## Animations

### GSAP (Scroll-triggered)

Used in: `ProblemSection`, `FeaturesSection`, `HowItWorks`, `FAQSection`

```typescript
gsap.fromTo(
  element,
  { opacity: 0, y: 30 },
  {
    opacity: 1, y: 0,
    scrollTrigger: {
      trigger: element,
      start: 'top 80%',
      toggleActions: 'play none none reverse',
    },
  }
);
```

### Framer Motion (Form transitions)

Used in: `BetaSignupForm`

```typescript
const slideVariants = {
  enter: { x: 50, opacity: 0 },
  center: { x: 0, opacity: 1 },
  exit: { x: -50, opacity: 0 },
};
```

---

## Known Issues & TODOs

### From `docs/slop.md` (Design Feedback)

| Issue | Priority | Status |
|-------|----------|--------|
| No product mockup in hero | High | 🔴 Not done |
| "Sound Familiar?" needs before/after cards | Medium | 🔴 Not done |
| UMaT badge should be more prominent | Medium | 🔴 Not done |
| Add student counter for social proof | Medium | 🔴 Not done |
| Soften background to dark navy | Low | 🔴 Not done |
| Add product screenshots | High | 🔴 Not done |

### Technical

| Task | Status |
|------|--------|
| Neon PostgreSQL `beta_signups` table | 🔴 Not done |
| Resend email integration | 🔴 Not done |
| API route for form submission | 🔴 Not done |
| Vercel deployment | 🔴 Not done |
| Custom domain setup | 🔴 Not done |

---

## Running Locally

```bash
cd sanko-beta
npm install
npm run dev
# Opens at http://localhost:5173
```

## Building for Production

```bash
cd sanko-beta
npm run build
npm run preview  # Test production build
```

## Deploying to Vercel

```bash
cd sanko-beta
npx vercel
```

---

## Environment Variables (Future)

```env
# Database
DATABASE_URL=postgres://...

# Email (Resend)
RESEND_API_KEY=re_xxxxx

# Analytics (Optional)
PLAUSIBLE_DOMAIN=beta.sankoslides.com
```

---

## Related Files

| File | Purpose |
|------|---------|
| [`/sanko-backend/app/models/university_context.py`](../sanko-backend/app/models/university_context.py) | University-specific rules (UMaT config) |
| [`/sanko-backend/app/crew/tools/academic_search_tool.py`](../sanko-backend/app/crew/tools/academic_search_tool.py) | Citation search (CrossRef, OpenAlex) |
| [`/docs/slop.md`](../docs/slop.md) | Design feedback and improvement checklist |

---

## Key Selling Points to Emphasize

When writing copy or making changes, these are the core differentiators:

1. **"Last-minute rescue"** — Students cramming at 11 PM is relatable
2. **Proper British English** — "colour" not "color" (lecturers mark this!)
3. **Real citations** — DOI-verified papers, not hallucinated references
4. **UMaT-specific** — Built with their formatting rules in mind
5. **SI units done right** — "50 kg" not "50kg" (common mistake)

---

## Contact

For questions about this project, refer to the main [README.md](../README.md).
