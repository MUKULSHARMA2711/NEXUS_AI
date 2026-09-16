# NEXUS — Development Principles & Guidelines

> **Status**: Phase 0 Specification  
> **Audience**: Core Developers & Contributors

---

## 1. Core Development Principles

These principles govern all development within the NEXUS repository. Every contributor and implementation engineer must adhere strictly to these guidelines.

---

### 1. Windows Development Environment
- The primary development host is Windows.
- Shell scripts and terminal commands must be compatible with Windows environments (PowerShell / Command Prompt) and cross-platform tools.
- File path handling in all codebases must be OS-agnostic (use Python's `pathlib.Path` or standard library utilities; avoid hardcoded UNIX slashes).
- Git line-ending configurations should respect cross-platform conventions (`core.autocrlf` or explicit `.gitattributes`).

---

### 2. No GPU-Dependent Development
- Local development workflows must never require a dedicated physical GPU.
- All local tasks (running APIs, background jobs, test suites, local embeddings or small models) must execute reliably on standard CPU hardware.
- High-compute operations, large language model inference, and heavy vector embeddings will leverage remote cloud API providers or lightweight CPU-optimized libraries.

---

### 3. Environment Variables Stored Through `.env`
- Configuration must follow Twelve-Factor App principles.
- Local configuration is loaded from a local `.env` file at the repository root.
- A tracked [`.env.example`](file:///c:/Users/mukul/OneDrive/Desktop/NEXUS/.env.example) file maintains all supported environment variables with descriptive placeholder values.
- Applications must fail fast on startup with clear error messages if required environment variables are absent.

---

### 4. Secrets Must Never Be Committed
- API keys, database passwords, tokens (GitHub, Jira, LLMs), and encryption secrets must never be committed to version control.
- `.gitignore` explicitly excludes all `.env` files, credentials, and local secret stores.
- Contributors should run secret-scanning tools prior to pushing commits.

---

### 5. Features Should Be Tested
- No feature is considered complete without automated tests.
- Every functional module must include unit tests verifying core logic and error boundaries.
- Integration tests must validate interactions between subsystems (e.g., API to database, ingestion worker to normalization layer).
- Regressions must be accompanied by reproducing test cases before fixes are applied.

---

### 6. Prefer Simple Architecture Over Unnecessary Complexity
- Avoid premature optimization and unnecessary abstractions.
- Introduce libraries, frameworks, or infrastructure components *only* when there is an immediate, demonstrable architectural problem that requires them.
- Do not build speculative features or complex distributed mechanisms until simpler approaches prove insufficient.

---

### 7. Docker Will Eventually Provide Reproducibility
- In future phases, Docker and Docker Compose definitions will be introduced to standardize local service dependencies (PostgreSQL, Redis, local mocks).
- Applications should remain easy to run both bare-metal on the host and containerized within Docker.

---

### 8. CI/CD Will Be Added Later
- Continuous Integration and Continuous Deployment (GitHub Actions) are planned for subsequent phases.
- Early development will focus on establishing clean code boundaries, reliable local test runners, and automated formatting/linting scripts before CI pipeline activation.

---

### 9. Observability Will Be Added Later
- Production-grade observability (OpenTelemetry tracing, Prometheus metrics, Grafana dashboards) will be systematically integrated in later phases.
- Early code should maintain clean logging practices (structured logging, clear log levels) to facilitate seamless instrumentation when observability tools are added.

---

### 10. AI Systems Must Be Evaluated, Not Judged Only by Demos
- Demonstrations and prompt tweaks are insufficient to establish AI reliability.
- NEXUS requires empirical evaluation frameworks:
  - Retrieval performance must be benchmarked using deterministic metrics (Recall@K, MRR, NDCG).
  - Reasoning and synthesis must be validated against curated golden datasets.
  - Evidence verification accuracy must be tested to ensure hallucinations are systematically detected and rejected.
- Changes to prompts, models, chunking strategies, or retrieval pipelines must be measured against baseline evaluation benchmarks.
