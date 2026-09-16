# NEXUS — High-Level System Architecture

> **Status**: Phase 0 Specification  
> **Audience**: Engineering Team & Architectural Reviewers

---

## 1. Architectural Overview

NEXUS is designed as a modular, decoupled engineering intelligence platform. The architecture separates synchronous user-facing query flows from asynchronous data ingestion pipelines and autonomous AI investigation loops.

The end-to-end system topology follows a structured, layered hierarchy:

```text
Frontend (React UI)
       │
       ▼
FastAPI API Gateway
       │
       ▼
Application / Services Layer
       │
       ▼
PostgreSQL + Redis (Persistence & Caching)
       │
       ▼
Ingestion / Indexing Subsystem
       │
       ▼
Retrieval Engine (Hybrid Vector & Lexical)
       │
       ▼
Reranking Engine
       │
       ▼
AI Reasoning / Tools Subsystem
       │
       ▼
Evidence Verification Subsystem
       │
       ▼
Structured Response with Citations
```

---

## 2. Core Architectural Paths

To maintain system reliability, high responsiveness, and strict factual correctness, NEXUS explicitly isolates three distinct execution paths:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. User Request Path                                                        │
│    User Query ──► API ──► Services ──► Retrieval ──► Synthesis ──► UI       │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. Asynchronous Ingestion Path                                             │
│    External Sources ──► Ingestion Workers ──► Normalization ──► Indexes     │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. AI Investigation Path                                                    │
│    Incident / Complex Task ──► Agent Loop ──► Tool Actions ──► Verification │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Path 1: User Request Path (Synchronous / Streaming)

The User Request Path handles interactive queries from engineers using the web frontend or developer CLI.

1. **Client Interaction**: The user submits a question or search query via the frontend.
2. **API Ingress**: The query hits the FastAPI layer, where authentication, authorization, and rate limiting are applied.
3. **Service Layer Dispatch**: The application services layer coordinates session context and evaluates query intent.
4. **Targeted Retrieval**: The retrieval engine fetches relevant context (code snippets, discussions, tickets, docs) using hybrid search.
5. **Reranking**: Candidate matches are scored and reordered based on query relevance and recency.
6. **Reasoning & Synthesis**: The AI layer synthesizes an answer strictly grounded on the retrieved snippets.
7. **Evidence Verification**: Factual claims are checked against the source text before delivery.
8. **Structured Delivery**: The response is returned to the client as a typed payload or stream, containing text and explicit citation anchors.

---

### Path 2: Asynchronous Ingestion Path (Background / Batch)

The Asynchronous Ingestion Path ensures that engineering artifacts across diverse source systems are continuously ingested and kept up-to-date without impacting user-facing query latency.

1. **Source Connectors**: Periodic workers or webhook handlers poll external engineering platforms (GitHub repositories, Jira tickets, documentation wikis, incident logs).
2. **Queueing & Scheduling**: Redis-backed task queues manage ingestion workloads, handling backoff, rate limits, and job retries.
3. **Normalization**: Heterogeneous raw payloads are transformed into canonical engineering entities with standard schemas (title, author, timestamp, URI, body).
4. **Chunking & Indexing**: Content is split into semantically coherent chunks, enriched with metadata, and converted into dense embeddings.
5. **Dual Persistence**:
   - Structured metadata and entity state are persisted in PostgreSQL.
   - Embeddings and searchable text representations are indexed into the search subsystem.

---

### Path 3: AI Investigation Path (Autonomous / Multi-Step)

The AI Investigation Path is invoked when a query requires complex multi-step diagnostics, incident root-cause analysis, or cross-repository forensics.

1. **Investigation Initialization**: Triggered by an incident identifier, error trace, or explicit deep-dive request.
2. **Hypothesis Formulation**: The AI agent creates an initial plan and identifies information gaps.
3. **Tool Execution Loop**: The agent iteratively invokes internal tools:
   - Git blame and commit diff inspections
   - Dependency graph traversals
   - Jira ticket and comment history queries
   - Runtime log correlation
4. **Evidence Collection**: Each tool execution yields candidate evidence artifacts bound to explicit sources and timestamps.
5. **Cross-Examination & Verification**: The collected evidence is verified for internal consistency and source authenticity.
6. **Investigation Report Generation**: The agent compiles a comprehensive, step-by-step investigation narrative where every conclusion is pinned to tangible evidence.

---

## 3. Structural Boundaries & Separation of Concerns

- **API vs. Worker Separation**: Fast, non-blocking API workers handle client interactions. Heavy ingestion, embedding generation, and multi-step investigation loops execute on asynchronous workers.
- **Stateless Application Layer**: Business logic remains stateless; state is externalized to PostgreSQL (durable records) and Redis (ephemeral caching, queues).
- **Decoupled AI Layer**: AI reasoning is treated as an isolated domain service. The rest of the platform interacts with AI services via typed contracts, allowing model providers and prompt strategies to evolve independently.
- **Verification Gate**: The Evidence Verification subsystem acts as a mandatory validation layer between raw LLM outputs and the presentation layer.

*(Note: Concrete library choices, low-level schemas, and transport protocols will be determined in subsequent phases.)*
