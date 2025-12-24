# Getting Started

This guide walks you through setting up the SankoSlides frontend for local development.

## Prerequisites

- **Node.js 20+** — [Download](https://nodejs.org/)
- **npm** (comes with Node.js) or pnpm
- **Firebase Project** — [Create one](https://console.firebase.google.com/)
- **Neon Database** — [Create free account](https://neon.tech/)
- **sanko-backend** running at `localhost:8080`

## Step 1: Clone & Install

```bash
cd sanko-frontend
npm install
```

## Step 2: Firebase Setup

### Create Firebase Project
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project
3. Enable Authentication with Email/Password and Google providers
4. Get your web app config from Project Settings → General

### Generate Service Account
1. Project Settings → Service Accounts
2. Generate new private key
3. Save JSON file in the project root

## Step 3: Database Setup

### Create Neon Database
1. Sign up at [neon.tech](https://neon.tech/)
2. Create a new project
3. Copy the connection string

### Run Migrations
```bash
npx drizzle-kit push
```

## Step 4: Environment Variables

Create `.env.local`:

```env
# Firebase Client
NEXT_PUBLIC_FIREBASE_API_KEY=AIza...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your-project
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=123456789
NEXT_PUBLIC_FIREBASE_APP_ID=1:123456789:web:abc123

# Firebase Admin (server-side)
GOOGLE_APPLICATION_CREDENTIALS=./your-service-account.json

# Database
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require

# Backend
NEXT_PUBLIC_API_URL=http://localhost:8080
```

## Step 5: Start Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Step 6: Start Backend

The frontend requires the Python backend to be running:

```bash
cd ../sanko-backend
# Follow backend setup instructions
uvicorn main:app --reload --port 8080
```

---

## Development Workflow

### Common Tasks

| Task | Command |
|------|---------|
| Start dev server | `npm run dev` |
| Build production | `npm run build` |
| Run linter | `npm run lint` |
| Push DB changes | `npx drizzle-kit push` |
| Generate DB types | `npx drizzle-kit generate` |

### Project Structure Tips

- **Pages** → `app/` directory (App Router)
- **New UI component** → `components/ui/`
- **Feature component** → `components/<feature>/`
- **API routes** → `app/api/`
- **Database changes** → `lib/db/schema.ts`

---

## Troubleshooting

### "Firebase not initialized"
Ensure all `NEXT_PUBLIC_FIREBASE_*` variables are set correctly.

### Database connection errors
- Check `DATABASE_URL` format
- Verify Neon project is active
- Confirm SSL mode is enabled

### Backend connection refused
- Ensure sanko-backend is running on port 8080
- Check `NEXT_PUBLIC_API_URL` matches backend URI
