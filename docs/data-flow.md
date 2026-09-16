# NEXUS — Data Lifecycle & Data Flow

> **Status**: Phase 0 Specification  
> **Audience**: Engineering Team & Contributors

---

## 1. The Data Lifecycle Pipeline

Data in NEXUS moves through a deterministic, unidirectional lifecycle. Every stage transforms raw external artifacts into verified, queryable intelligence.

```text
External Engineering Sources
             │
             ▼
         Ingestion
             │
             ▼
       Normalization
             │
             ▼
    Chunking / Indexing
             │
             ▼
Metadata + Searchable Representation
             │
             ▼
      Hybrid Retrieval
             │
             ▼
         Reranking
             │
             ▼
       AI Reasoning
             │
             ▼
   Evidence Verification
             │
             ▼
     Answer + Citations
```

---

## 2. Stage Breakdown

### 1. External Engineering Sources
The data lifecycle begins at the perimeter of the software engineering ecosystem:
- **Source Control**: Git repositories, branches, tags, commits, tree blobs, diffs, pull request comments, and code reviews.
- **Issue Trackers**: Jira issues, GitHub Issues, bug trackers, sprint boards, labels, and transition histories.
- **Documentation**: Markdown files, READMEs, RFCs, Architecture Decision Records (ADRs), and internal wikis.
- **Observability & Incident Logs**: Post-mortems, incident timelines, alerts, error logs, and deployment events.

### 2. Ingestion
- **Acquisition**: Triggered via real-time webhooks (e.g., `pull_request.closed`, `push`, `issue.created`) or scheduled batch pollers.
- **Resilience**: Ingestion jobs are buffered into background queues, isolating external rate limits and downtime from the platform core.
- **Provenance Capture**: Raw payloads are recorded alongside ingest metadata (source system identifier, payload checksum, synchronization timestamp).

### 3. Normalization
- **Canonical Schema Mapping**: Raw, heterogeneous payloads from distinct systems are transformed into uniform internal entities:
  - Artifact Identity (canonical URI)
  - Entity Type (commit, PR, issue, file, doc, incident)
  - Authorship (standardized author IDs, committers, assignees)
  - Temporal Metadata (created at, committed at, merged at, resolved at)
  - Content Body (cleaned text, markdown, or diff representation)
- **Sanitization**: Secret masking, redaction of sensitive tokens, and noise reduction (removal of generated boilerplate, minified assets).

### 4. Chunking / Indexing
- **Semantic Chunking**: Text and code are split into context-preserving segments:
  - Code chunking respects language AST / syntax boundaries (functions, classes, modules).
  - Prose/ticket chunking respects section headers and paragraph structures.
- **Vector Embedding**: Text chunks pass through embedding models to generate dense semantic vectors.
- **Lexical Tokenization**: Text chunks are tokenized, stemmed, and processed for full-text keyword indexing.

### 5. Metadata + Searchable Representation
- **Relational Storage**: Core entity relationships, hierarchy, foreign keys, and temporal fields are persisted in PostgreSQL.
- **Dual Representation**:
  - *Dense Vector Store*: Optimized for semantic similarity and conceptual search.
  - *Sparse Lexical Store*: Optimized for exact identifier lookups (commit SHAs, error codes, function names, issue keys like `PROJ-1234`).
- **Unified Identity**: Every chunk maintains an immutable link back to its parent entity and source location (line ranges, file paths, commit hashes).

### 6. Hybrid Retrieval
- **Query Processing**: Incoming queries are analyzed to generate both lexical query terms and semantic dense query vectors.
- **Parallel Dispatch**: The retrieval engine queries both dense and sparse indexes concurrently.
- **Metadata Filtering**: Results are filtered by scope (repository, author, date range, branch, artifact type).
- **Fusion**: Candidates from lexical and semantic searches are merged (e.g., via Reciprocal Rank Fusion) into a unified candidate pool.

### 7. Reranking
- **Cross-Encoder Scoring**: Top candidate chunks pass through a reranking layer.
- **Deep Relevance Assessment**: The reranker jointly computes query-document interaction scores, reordering candidates based on precise relevance, context fit, and temporal recency.
- **Window Pruning**: Low-scoring and redundant chunks are discarded to fit the optimal context window for downstream reasoning.

### 8. AI Reasoning
- **Context Assembly**: High-confidence evidence chunks are assembled into a structured prompt context.
- **Constraint Enforcement**: The reasoning model is instructed to construct arguments using *only* the supplied context.
- **Hypothesis Evaluation**: For multi-step queries, intermediate conclusions are derived and verified through further tool calls if required.

### 9. Evidence Verification
- **Claim Extraction**: The generated output is decomposed into individual factual assertions.
- **Source Grounding Check**: Each claim is checked against the retrieved evidence text to verify factual consistency.
- **Hallucination Rejection**: Any claim lacking verbatim or semantic support in the retrieved evidence is flagged, rejected, or regenerated.

### 10. Answer + Citations
- **Delivery**: The synthesized answer is emitted with embedded citation markers.
- **Structured Anchors**: Each citation links directly to the source artifact:
  - Canonical URL / File path
  - Line numbers / range
  - Commit SHA / Version ID
  - Author and timestamp
- **Deterministic Traceability**: The consumer can independently inspect and verify every piece of evidence backing the answer.
