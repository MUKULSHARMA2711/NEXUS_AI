# ADR-001: NEXUS Architecture Baseline

## Status

Accepted

---

## Context

NEXUS is an AI Engineering Intelligence Platform that unifies, indexes, and reasons across heterogeneous engineering artifacts (code repositories, pull requests, issue trackers, documentation, and incident logs). To accomplish this, the platform must integrate:

* Engineering data ingestion from distributed external systems
* Relational engineering metadata and entity relationship management
* Hybrid search and retrieval (lexical keyword and dense semantic vector search)
* AI reasoning and synthesis
* Strict evidence verification and citation anchoring
* Asynchronous background job processing and queueing
* Authentication, authorization, and tenant/workspace boundaries
* System observability and operational monitoring
* Empirical AI and retrieval evaluation frameworks

The platform is developed on a Windows laptop without a dedicated GPU. Therefore, local development and continuous workflows must not depend on local large-model inference or local model training.

Furthermore, the architecture must avoid premature complexity, cargo-culting, and speculative distributed patterns. The project prioritizes genuine engineering requirements over unnecessary technology.

---

## Decisions

### 1. Backend Architecture: Modular Monolith
* **Decision**: Build the backend as a **modular monolith** using **Python** and **FastAPI**.
* **Internal Boundaries**: The codebase will enforce strict internal module boundaries:
  * `api` — HTTP endpoints, request routing, and serialization
  * `authentication` — User identity, tokens, RBAC, and credential validation
  * `domain` — Core business logic, workspaces, and entity relationships
  * `ingestion` — External connector dispatch, job orchestration, and normalization
  * `retrieval` — Search coordination, hybrid search fusion, and reranking
  * `ai` — LLM client orchestration, prompt templating, and reasoning workflows
  * `evidence` — Claim extraction, citation parsing, and source ground-truth verification
  * `evaluation` — Benchmark harnesses, golden datasets, and quality metrics
* **Microservices Policy**: Microservices are explicitly rejected for initial development. All modules will reside in a single deployable unit with clean programmatic interfaces.

### 2. Python Dependency Management: `uv`
* **Decision**: Adopt **`uv`** as the standard package installer, virtual environment manager, and resolver for the Python backend.
* **Rationale**: Fast resolution, cross-platform reproducibility on Windows, and lockfile fidelity without the runtime overhead or complexity of heavier managers.

### 3. Frontend Architecture: React + TypeScript + Vite + Tailwind CSS
* **Decision**: Build the client application using:
  * **React** with **TypeScript** for typed component state and interactive UI
  * **Vite** as the fast local development server and bundler
  * **Tailwind CSS** for maintainable, utility-first styling
  * **npm** as the initial frontend package manager

### 4. Primary Database: PostgreSQL
* **Decision**: Use **PostgreSQL** as the primary system of record for all relational engineering metadata, entities, user accounts, and ingestion sync states.

### 5. Vector Search: PostgreSQL with `pgvector`
* **Decision**: Use **PostgreSQL with the `pgvector` extension** for initial vector storage, indexing, and similarity search.
* **Policy**: Do not introduce a standalone or dedicated vector database unless future scale, throughput measurements, or distinct operational requirements justify it.

### 6. Background Processing: Redis & Celery
* **Decision**:
  * Use **Redis** as the infrastructure backbone for task queueing, message brokering, and transient caching.
  * Use **Celery** as the background task execution engine for asynchronous ingestion, payload normalization, and batch indexing workers.

### 7. LLM Infrastructure: Hosted LLM APIs via Internal Abstraction
* **Decision**: Utilize **hosted LLM APIs** (cloud provider endpoints) for reasoning, synthesis, and text embeddings.
* **Provider Abstraction**: All LLM client interactions must be encapsulated behind an internal interface/adapter layer, allowing models or providers to be swapped without modifying domain or retrieval services.
* **Hardware Policy**: The platform will not be designed around or depend on local GPU inference.

### 8. Agent Framework: Deferred Selection
* **Decision**: **Do not select a third-party agent framework yet.**
* **Rationale**: Custom agent orchestration primitives and framework trade-offs will be formally evaluated when Phase 6 begins. Early investigation loops will use direct, deterministic Python tool dispatching.

### 9. Streaming Transport: Deferred Protocol Selection
* **Decision**: **Do not commit to Server-Sent Events (SSE) or WebSockets yet.**
* **Rationale**: The specific streaming mechanism will be selected when the interactive streaming requirement is implemented in the API and frontend phases.

### 10. Deployment: Docker
* **Decision**: Standardize packaging and dependency orchestration using **Docker** and **Docker Compose** to ensure parity between Windows local development and production environments.

### 11. Continuous Integration / Continuous Deployment: GitHub Actions
* **Decision**: Use **GitHub Actions** for CI/CD pipelines (linting, type checking, test suites, and container image builds) when automation is introduced.

### 12. Observability: OpenTelemetry, Prometheus & Grafana
* **Decision**: Structure backend services and logging from day one so that **OpenTelemetry** distributed tracing can be integrated without breaking architectural refactors.
* **Timeline**: Prometheus metrics collection and Grafana dashboards will be added later when the dedicated observability phase begins.

---

## Architectural Principles

Every technical decision in NEXUS must adhere to these ten principles:

1. **Evidence before assertion**: The platform must never produce an unverified claim. Every synthesized statement must be backed by retrieved evidence.
2. **Simple architecture before distributed architecture**: Maximize single-process and modular architectures before introducing distributed boundaries.
3. **Measure before optimizing**: Avoid speculative performance optimizations; profile bottlenecks with concrete metrics.
4. **Evaluate AI behavior empirically**: Evaluate search, retrieval, and LLM reasoning using deterministic metrics, golden sets, and automated evaluation suites rather than subjective demos.
5. **Keep external providers behind abstractions**: Cloud LLMs, search engines, and third-party APIs must be isolated behind domain interfaces.
6. **Never commit secrets**: Credentials, tokens, and private keys must be stored strictly in `.env` files and excluded from source control.
7. **Asynchronous work must be resilient to retries and failures**: Ingestion jobs and worker tasks must be idempotent and resilient to intermittent network failures and external rate limits.
8. **Important AI claims should be traceable to evidence**: Factual outputs must preserve the link chain: $\text{Claim} \rightarrow \text{Evidence} \rightarrow \text{Source} \rightarrow \text{Timestamp}$.
9. **Data lineage must be preserved**: When data is normalized and indexed, its provenance (commit hash, author, origin URI, timestamp) must be immutably recorded.
10. **Technologies must solve actual engineering problems**: Do not adopt libraries or infrastructure unless they solve an immediate, demonstrable architectural challenge.

---

## Consequences

### Positive Consequences
* **Operational Simplicity**: A modular monolith backed by PostgreSQL and Redis keeps the deployment topology compact and straightforward to manage, especially on a single Windows development machine.
* **Unified Persistence**: Using PostgreSQL with `pgvector` eliminates dual-write synchronization issues between relational metadata and vector embeddings, enabling atomic transactions and joint relational-vector SQL queries.
* **Asynchronous Resilience**: Celery and Redis provide battle-tested worker infrastructure with built-in retry mechanisms, rate limiting, and failure isolation for heavy ingestion tasks.
* **Fast Developer Loop**: `uv` and `Vite` ensure near-instant dependency resolution and hot reloading, accelerating local development cycles.
* **Vendor Portability**: Internal abstractions around LLM providers prevent vendor lock-in and enable smooth migration across models.
* **Reduced Premature Abstraction**: Deferring agent frameworks and streaming protocols prevents over-engineering before functional requirements are clear.

### Negative Consequences / Trade-offs
* **Operational Footprint of Celery**: Introducing Celery requires running Redis and Celery worker processes alongside the FastAPI server during local development.
* **pgvector Scale Limits**: While `pgvector` is ideal for initial and intermediate scales, extremely large datasets (tens of millions of high-dimensional vectors with high QPS) may eventually require dedicated indexing tuning or specialized vector engines.
* **Cloud API Dependency & Cost**: Relying exclusively on hosted LLM APIs incurs external API consumption costs, latency over the public internet, and strict rate limits.
* **Monolith Scaling Limits**: As the codebase expands across multiple teams in the long term, module boundaries must be strictly policed by automated linting and architecture tests to prevent code coupling.

---

## Rejected / Deferred Decisions

The following architectural choices are intentionally rejected or deferred at this time:

* **Dedicated Vector Database (Pinecone, Qdrant, Milvus, Weaviate)**: Deferred. PostgreSQL with `pgvector` is sufficient for baseline and intermediate workloads.
* **Microservices Architecture**: Rejected for the current lifecycle. A modular monolith provides lower latency, simpler deployment, and zero network serialization overhead.
* **Kubernetes**: Rejected for Phase 0. Docker and Docker Compose provide sufficient containerization without K8s operational overhead.
* **Third-Party Agent Frameworks (LangChain, CrewAI, AutoGen)**: Deferred. Will be evaluated empirically in Phase 6.
* **SSE vs. WebSockets Decision**: Deferred until the streaming feature requirement is implemented.
* **Local Large-Model Serving (Ollama, vLLM, local HuggingFace models)**: Rejected. Incompatible with the target Windows non-GPU local development constraint.
* **Kafka / Distributed Event Streaming**: Rejected. Redis queues provide adequate throughput and simplicity for current asynchronous workloads.
