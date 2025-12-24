# Components Reference

## Authentication

### `AuthProvider`
**Path:** `components/auth-provider.tsx`

Global authentication context wrapping the app.

**Provides:**
- `user` — Firebase User object
- `dbUser` — Database user record (synced from Neon)
- `loginWithEmail()`, `registerWithEmail()`, `loginWithGoogle()`, `signOut()`
- `syncUser()` — Force re-sync with database

---

## Editor Components

Located in `components/editor/`

### `ClarifierChat`
Conversational interface for the "negotiation" phase. Users answer clarifying questions to refine their presentation requirements.

**Props:**
| Prop | Type | Description |
|------|------|-------------|
| `projectId` | string | Current project UUID |
| `mode` | string | Generation mode (replica/synthesis/deep_research) |
| `onOrderComplete` | (sessionId) => void | Callback when clarification completes |
| `readOnly` | boolean | Disable input |
| `onAgentChange` | (agent) => void | Current agent callback |

**Features:**
- Markdown rendering in messages
- File attachment support
- Thinking indicator
- ConfirmationCard for order approval

### `BlueprintReview`
Displays the generated outline/skeleton for user approval.

### `GenerationProgress`
Real-time progress visualization during slide generation.

**Features:**
- Agent status tracking (planner → generator → visual_qa)
- Tool call visualization
- SSE event consumption
- Duration and cost metrics

### `SlideViewer`
Displays generated slides with navigation.

---

## Dashboard Components

Located in `components/dashboard/`

| Component | Description |
|-----------|-------------|
| `DashboardShell` | Layout wrapper |
| `ModeSelector` | Card-based mode selection |
| `ProjectCard` | Individual project display |
| `ProjectList` | Project grid/list with filters |
| `UserNav` | User dropdown menu |

---

## Playground Components

Located in `components/playground/`

| Component | Description |
|-----------|-------------|
| `PlaygroundWorkspace` | Full API testing environment |
| `MetricsDashboard` | Token usage and cost visualization |
| `SessionHistory` | Previous session browser |

---

## UI Components

Located in `components/ui/` — Built on shadcn/ui + Radix primitives.

| Component | Based On |
|-----------|----------|
| `Button` | Radix Slot + CVA |
| `Dialog` | Radix Dialog |
| `DropdownMenu` | Radix DropdownMenu |
| `Select` | Radix Select |
| `Tabs` | Radix Tabs |
| `Card` | Custom |
| `Input`, `Textarea` | Native + styling |
| `Field` | Label + input composition |
| `AlertDialog` | Radix AlertDialog |
| `Sheet` | Radix Dialog (slide-out) |
| `Switch` | Radix Switch |
