# NEXUS — Frontend Application

> **Status**: Phase 0 — Foundation (Not yet implemented)  
> **Technology Stack**: React, TypeScript, Tailwind CSS

---

## 1. Overview

The `frontend/` directory will house the client-side single-page application (SPA) for NEXUS. The frontend provides engineers, tech leads, and leadership with an intuitive, high-performance interface to explore engineering intelligence, inspect incident timelines, and review evidence-backed technical answers.

---

## 2. Future Core Responsibilities

The React frontend will be structured around key functional domains:

### 1. Engineering Dashboard
- Display platform health, connected repository synchronization statuses, and ingestion throughput.
- Provide high-level organizational metrics (active incidents, recently indexed PRs, frequently queried services).
- Quick-launch widgets for recent investigations and saved search filters.

### 2. Engineering Search
- Unified search experience combining natural language semantic queries with exact keyword lookups.
- Rich filtering controls (by repository, author, date range, file extension, pull request, Jira ticket status).
- Fast, keyboard-navigable search results displaying snippet previews and metadata badges.

### 3. Investigations Interface
- Interactive workspace for multi-step AI investigations (e.g., bug forensics, architecture queries, legacy code analysis).
- Step-by-step trace visualization showing agent hypotheses, intermediate tool actions, and discovered clues.
- Collaborative workspace allowing engineers to append notes, refine queries, and export investigation findings.

### 4. Incidents & Post-Mortem Explorer
- Dedicated views for outage timelines and incident post-mortems.
- Chronological correlation mapping code commits, alerts, deployment events, and chat discussions leading up to an incident.
- Automated generation and interactive review of incident post-mortem drafts.

### 5. Evidence Visualization
- Rich citation viewer rendering source artifacts side-by-side with AI-synthesized claims.
- Syntax-highlighted code diff and snippet inspection with line-number anchoring.
- Interactive verification badges indicating claim confidence, source origin, and timestamp validity.

### 6. Authentication & User Profile
- User login, single sign-on (SSO), and session management.
- API key generation and personal workspace preferences.
- Role-based view adjustments (engineer vs. administrator).

### 7. Evaluation & Observability Views
- Internal dashboards to inspect retrieval quality, precision/recall metrics, and latency across search tiers.
- AI trace inspection tooling to analyze prompt tokens, completion times, and evidence verification passes.
- Ground-truth evaluation test run visualizer.

---

## 3. Directory Structure (Planned)

```text
frontend/
├── src/
│   ├── components/      # Reusable UI primitives (buttons, modals, badges)
│   ├── features/        # Feature-based domain modules
│   │   ├── auth/        # Authentication views & forms
│   │   ├── dashboard/   # High-level overview dashboards
│   │   ├── search/      # Unified engineering search
│   │   ├── investigations/ # Multi-step investigation workbench
│   │   ├── incidents/   # Incident timeline & forensic views
│   │   ├── evidence/    # Citation inspector & code diff viewer
│   │   └── evaluation/  # Observability & evaluation metrics
│   ├── hooks/           # Custom React hooks
│   ├── services/        # API client and WebSocket handlers
│   ├── styles/          # Tailwind CSS configurations
│   ├── types/           # TypeScript interfaces and domain types
│   ├── App.tsx          # Root application component
│   └── main.tsx         # React DOM entrypoint
├── package.json         # Node dependencies
└── vite.config.ts       # Vite configuration
```

*(Note: Implementation will begin in Phase 5 per the guidance of the architect/technical lead.)*
