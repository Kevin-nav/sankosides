# API Routes

The frontend includes API routes that serve as a Backend-for-Frontend (BFF) layer, handling authentication and proxying requests to the Python backend.

## Authentication

### `POST /api/auth/sync`
Syncs Firebase user to the Neon database.

**Headers:** `Authorization: Bearer <firebase-id-token>`

**Response:**
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "displayName": "User Name",
    "subscriptionTier": "free",
    "universityProfile": null
  }
}
```

---

## Generation API

Routes under `/api/generate/` orchestrate the AI generation pipeline.

### Session Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/generate/start` | POST | Create new generation session |
| `/api/generate/status/[sessionId]` | GET | Get session status |

### Clarification Phase

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/generate/clarify/[sessionId]` | POST | Send clarification message |
| `/api/generate/clarify/[sessionId]/stream` | GET | SSE stream for responses |

### Outline Phase

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/generate/outline/[sessionId]` | GET | Get generated skeleton |
| `/api/generate/approve-outline/[sessionId]` | POST | Approve with modifications |

### Generation Phase

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/generate/generate/[sessionId]` | POST | Start slide generation |
| `/api/generate/events/[sessionId]` | GET | SSE stream for progress |
| `/api/generate/stream/[sessionId]` | GET | Alternative progress stream |
| `/api/generate/result/[sessionId]` | GET | Get final presentation |

### Utilities

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/generate/prompts` | GET | List available prompts |
| `/api/generate/prompts/[name]` | GET | Get specific prompt |
| `/api/generate/metrics/[sessionId]` | GET | Token usage & costs |
| `/api/generate/blueprint/[sessionId]` | GET | Get blueprint JSON |
| `/api/generate/confirm/[sessionId]` | POST | Confirm order form |

---

## Projects

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/projects` | GET | List user's projects |
| `/api/projects` | POST | Create new project |
| `/api/projects/[id]` | GET | Get project details |
| `/api/projects/[id]` | PATCH | Update project |
| `/api/projects/[id]` | DELETE | Delete project |

---

## User

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/user/profile` | GET | Get user profile |
| `/api/user/profile` | PATCH | Update profile |
| `/api/user/preferences` | PATCH | Update preferences |

---

## Metrics

### `GET /api/metrics/summary`
Dashboard metrics for the current user.

---

## Backend Proxy

The `next.config.ts` includes a rewrite rule:
```
/api/generation/:path* → http://127.0.0.1:8080/api/generation/:path*
```

This proxies any unhandled generation routes directly to the Python backend.
