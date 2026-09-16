# NEXUS — Testing & Quality Assurance Strategy

> **Status**: Phase 0 — Foundation  
> **Audience**: All Contributors & Implementation Engineers

---

## 1. Overview

NEXUS is a mission-critical platform where correctness and truthfulness are essential. Because the platform synthesizes engineering intelligence and conducts automated diagnostics, standard software testing alone is insufficient. 

Our testing strategy spans both classical deterministic testing (unit, integration, API, end-to-end) and specialized empirical AI evaluation (retrieval benchmarks, claim verification accuracy).

---

## 2. Testing Tiers & Intended Strategy

```text
┌──────────────────────────────────────────────────────────────────┐
│                   End-to-End Tests (E2E)                         │
├──────────────────────────────────────────────────────────────────┤
│           AI & Evaluation Tests (Retrieval & Synthesis)           │
├──────────────────────────────────────────────────────────────────┤
│                      API & Contract Tests                        │
├──────────────────────────────────────────────────────────────────┤
│                       Integration Tests                          │
├──────────────────────────────────────────────────────────────────┤
│                          Unit Tests                              │
└──────────────────────────────────────────────────────────────────┘
```

---

### 1. Unit Tests
- **Scope**: Isolated testing of pure functions, utility modules, and domain models without external network or database dependencies.
- **Coverage Targets**:
  - Text normalization routines and sanitization filters.
  - Chunking splitters (AST code parsing, markdown boundary splits).
  - Citation parser and data formatting helpers.
  - Pydantic schema validation rules.

### 2. Integration Tests
- **Scope**: Verification of interactions across two or more subsystems.
- **Coverage Targets**:
  - Database persistence and query correctness against PostgreSQL test instances.
  - Task queue enqueueing, processing, and dead-letter handling via Redis.
  - Connector ingestion flows using recorded fixtures or mock server responses (GitHub REST/GraphQL, Jira API).
  - Search index synchronization and document lifecycle updates.

### 3. API Tests
- **Scope**: Functional testing of FastAPI routes, status codes, and payload contracts.
- **Coverage Targets**:
  - Authentication flows, token issuance, and expired token rejection.
  - Role-based authorization on protected endpoints.
  - Query parameter validation, error responses, and rate limit responses.
  - Streaming endpoint behavior (SSE / WebSockets).

### 4. Retrieval Tests
- **Scope**: Quantitative evaluation of the search and reranking subsystems against curated benchmark query sets.
- **Coverage Targets**:
  - **Recall@K and Mean Reciprocal Rank (MRR)**: Ensuring relevant code snippets and tickets appear within the top $K$ retrieved candidates.
  - **Lexical vs. Dense Hybrid Balance**: Ensuring exact keyword queries (e.g., commit hashes, error codes) and semantic conceptual queries both return expected items.
  - **Reranking Efficiency & Latency**: Verifying that cross-encoders maintain strict latency bounds while boosting true positives.

### 5. AI & Evaluation Tests
- **Scope**: Empirical testing of LLM reasoning, agent tool execution, and evidence verification pipelines using golden datasets.
- **Coverage Targets**:
  - **Evidence Grounding Ratio**: Verifying that synthesized claims strictly reference retrieved evidence.
  - **Hallucination Detection**: Intentionally passing ungrounded or adversarial context to verify that the verification engine flags and rejects false claims.
  - **Tool Invocation Accuracy**: Testing whether agentic workflows select correct tools and extract valid arguments during multi-step investigations.
  - **Evaluation Benchmarks**: Running reproducible test suites measuring fidelity, hallucination rates, and answer quality across model changes.

### 6. End-to-End Tests (E2E)
- **Scope**: Comprehensive workflow validation simulating real user operations from the browser interface down to the backend and data stores.
- **Coverage Targets**:
  - Ingesting a sample repository -> Running a search query -> Receiving a verified answer with interactive citations.
  - Initiating an incident investigation -> Reviewing the timeline -> Validating that linked citations accurately highlight the source diff.

---

## 3. Directory Layout (Planned)

```text
tests/
├── unit/            # Isolated unit test suites
├── integration/     # Service, database, and queue integration tests
├── api/             # FastAPI HTTP and WebSocket tests
├── retrieval/       # Search benchmarks and recall metrics
├── evaluation/      # Golden datasets, hallucination tests, and AI evaluations
├── e2e/             # Full system end-to-end workflows
├── fixtures/        # Mock payloads (GitHub PRs, Jira tickets, sample repos)
└── conftest.py      # Pytest fixtures and environment configuration
```

*(Note: Test implementations will accompany functional code starting in Phase 1.)*
