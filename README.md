# QueryMaster — Version-Aware RAG System

> **Design status:** The authoritative RAG requirements and data model are in
> [`docs/specs.md`](./docs/specs.md). The implementation sequence and acceptance
> criteria are in [`docs/plan.md`](./docs/plan.md). Architecture details below
> predate the finalized design and are retained as historical context only.

A Django-based Retrieval-Augmented Generation system that keeps FAQ and document knowledge continuously up to date, prevents stale answers, resolves conflicting information using the latest content, and returns traceable citations.

---

## Problem Statement

- Two knowledge sources: FAQs managed in Django Admin and uploaded documents in multiple formats.
- Both sources change at runtime; the next query must use only currently valid knowledge.
- Contradictory evidence must prefer the latest content (resolved by `updated_at`).
- Every answer must identify the exact FAQ or document it came from.

---

## Architecture Decisions

### Knowledge Sources

| Source | Management | Granularity |
|---|---|---|
| FAQs | Django Admin (staff only) | 1 FAQ = N chunks (512 tokens each) |
| Documents | Upload API (staff only) | Section/heading blocks → 512-token chunks, 64-token overlap |

**Supported document formats:** PDF (text layer via PyMuPDF), DOCX, XLSX, CSV, PPTX, TXT, Markdown.
Scanned PDF pages that yield no text are skipped — upload succeeds with a `pages_skipped` warning in the response.

### Model Providers — Strategy Pattern

Both embedding and LLM providers follow the **Strategy pattern** with a **Factory** to wire them from config. This means the provider implementation is swappable without touching business logic.

```
querymaster/ai/providers/
  embedding/
    base.py          ← EmbeddingProvider abstract class
    openai.py
    gemini.py
  llm/
    base.py          ← LLMProvider abstract class
    openai.py
    gemini.py
  reranker/
    base.py          ← RerankerProvider abstract class
    gemini.py
```

**Providers at launch:** OpenAI + Gemini for both embedding and LLM.

**Runtime switching:** LLM provider is switchable at runtime via `django-constance` (no redeploy needed). Embedding provider is **deploy-time only** — switching it invalidates all existing vectors and requires a full re-index via management command.

### Vector Store — pgvector

All embeddings stored in PostgreSQL via `pgvector`. Embedding dimension is fixed at **`vector(768)`**:
- Gemini `text-embedding-004` → native 768 dims
- OpenAI `text-embedding-3-small` → truncated to 768 via Matryoshka Representation Learning (MRL)

Fixed dimension means atomic revision switching stays inside a single Postgres transaction — no two-phase commit against an external store.

### Chunking Strategy

| Format | Block unit | Chunk size | Overlap |
|---|---|---|---|
| PDF / DOCX / TXT / MD | Heading section; fallback paragraph | 512 tokens | 64 tokens |
| PPTX | One slide = one block | 512 tokens | 64 tokens |
| XLSX / CSV | One sheet = one block | 512 tokens | 64 tokens |
| FAQ | Full Q+A text | 512 tokens | 64 tokens |

**Diff strategy:** On document update, only changed blocks are re-embedded (unchanged blocks reuse existing embeddings and `updated_at`). Block identity for docs is `(document_id, section_heading_hash)`. For FAQs, identity is at FAQ level — any edit to a FAQ drops and re-generates all its chunks with key `(faq_id, chunk_index)`.

### Document Identity

Documents are identified by **filename**. On upload:
1. System checks if a document with that filename already exists.
2. If yes → confirm "This will update [Document Name]" → diff and re-index changed blocks.
3. If no → create new document record and run full ingestion.

### Retrieval Pipeline — LangGraph

Query flow is a linear LangGraph state machine. Each step is a node in `querymaster/ai/nodes/`:

```
retrieve → rerank → deduplicate → resolve → generate (streaming)
```

| Node | What it does |
|---|---|
| `retrieve` | Hybrid search: pgvector similarity + Postgres full-text (BM25), merged via Reciprocal Rank Fusion |
| `rerank` | Gemini scores each chunk for relevance to the query |
| `deduplicate` | Drops chunks with identical content hash |
| `resolve` | Compares `updated_at` on contradicting chunks — newer wins. If sources conflict with identical `updated_at` (millisecond-level tie), FAQ beats document |
| `generate` | Streaming LLM call; citations assembled from resolved state |

### Versioning & Activation

- Every document upload creates a new **revision** that stays in `Processing` state during ingestion.
- Ingestion is **atomic all-or-nothing**: blocks are written to a staging table; on full success, a single transaction promotes them to active and retires the previous revision.
- Ingestion failure triggers auto-retry with exponential backoff (Celery built-in). After N retries, revision is marked `Failed` and surfaced in Django Admin.
- Only the active revision of each document/FAQ is searchable. Deleted sources are excluded immediately.

### Deletion

- **Soft delete only.** Deleted documents/FAQs are removed from retrieval immediately but preserved for audit.
- Restore goes straight back to `Active` — no re-ingestion needed since chunks are preserved.

### Ingestion Task Design (Celery)

Two-stage fan-out:
1. **Parse task** — extract text, run block diff, write unchanged blocks from old revision, queue embedding tasks for changed/new blocks.
2. **Embedding tasks** — fan out in batches of 20 blocks, each task embeds one batch and writes to staging.
3. **Activate task** — Celery chord callback; runs after all embedding tasks complete; atomically promotes staging to active revision.

### Citations

Each answer includes structured citations. `source_id` is internal only — never shown on the UI.

| Field | FAQ | Document |
|---|---|---|
| `source_type` | `faq` | `document` |
| `display_text` | FAQ question text | Document title + section heading |
| `location` | FAQ #{id} | Page number + section heading |
| `updated_at` | FAQ's `updated_at` | Block's `updated_at` |

### Streaming

Query responses stream via **Server-Sent Events (SSE)**. The LLM provider SDK streams tokens natively; the Django async view propagates them directly to the client via `StreamingHttpResponse`.

```
event: token        → {"text": "Refunds are"}
event: token        → {"text": " processed within 14 days"}
event: citations    → {"citations": [...]}
event: done         → {}
```

---

## API Endpoints

| Method | Endpoint | Access |
|---|---|---|
| `POST` | `/api/ai/v1/documents/upload/` | Staff only |
| `GET` | `/api/ai/v1/documents/` | Staff only |
| `GET` | `/api/ai/v1/documents/{id}/status/` | Staff only |
| `DELETE` | `/api/ai/v1/documents/{id}/` | Staff only (soft delete) |
| `POST` | `/api/ai/v1/documents/{id}/restore/` | Staff only |
| `POST` | `/api/ai/v1/query/` | Authenticated (SSE stream) |
| `GET` | `/api/ai/v1/query/{query_id}/` | Authenticated |
| `GET` | `/api/v1/users/faqs/` | Authenticated (read-only) |

---

## What We Have to Build

### 1. Data Models (`querymaster/ai/`)

- `Document` — filename, title, is_deleted, created_at, updated_at
- `DocumentRevision` — document FK, status (Processing/Active/Failed), embedding_provider, embedding_model, created_at
- `DocumentBlock` — revision FK, heading, page_number, content_hash, updated_at
- `DocumentChunk` — block FK, chunk_index, text, embedding `vector(768)`, updated_at
- `FAQRevision` — faq FK, status, embedding_provider, embedding_model
- `FAQChunk` — faq FK, chunk_index, text, embedding `vector(768)`, updated_at
- `QueryLog` — query text, answer, citations JSON, created_at, user FK

### 2. Provider Layer (`querymaster/ai/providers/`)

- Abstract base classes: `EmbeddingProvider`, `LLMProvider`, `RerankerProvider`
- Implementations: `OpenAIEmbedding`, `GeminiEmbedding`, `OpenAILLM`, `GeminiLLM`, `GeminiReranker`
- `ProviderFactory` — reads `django-constance` config and instantiates correct Strategy

### 3. Ingestion Pipeline (`querymaster/ai/`)

- **Parsers** (`utils/parsers/`) — one parser per format: PDF (PyMuPDF + per-page scanned-page detection), DOCX, XLSX, CSV, PPTX, TXT/MD
- **Block differ** (`utils/differ.py`) — compares old revision blocks to new parsed blocks by content hash; returns added/changed/removed sets
- **Celery tasks** (`tasks.py`) — `parse_document_task`, `embed_block_batch_task`, `activate_revision_task` (chord callback)

### 4. Retrieval Pipeline (`querymaster/ai/`)

- **Nodes** (`nodes/`) — `retrieve.py`, `rerank.py`, `deduplicate.py`, `resolve.py`, `generate.py`
- **Graph** (`graphs/query_graph.py`) — LangGraph `StateGraph` wiring all nodes with typed state
- **Hybrid search** (`utils/search.py`) — pgvector ANN query + `tsvector` full-text query, RRF merge

### 5. API Layer (`querymaster/ai/api/v1/`)

- Serializers for document upload, status, query request/response, citation shape
- Async streaming view for `/query/` using `StreamingHttpResponse` + SSE
- DRF views for document management endpoints

### 6. Admin Integration

- `DocumentAdmin` — list with revision status, ingestion failure detail, soft delete / restore actions
- `FAQAdmin` — existing Django Admin, extended with chunk count and last indexed timestamp

### 7. Tests

- Ingestion: assert unchanged blocks reuse embeddings, changed blocks get new `updated_at`
- Atomic activation: assert failed ingestion leaves previous active revision intact
- Retrieval: assert deleted sources never appear in results
- Contradiction resolution: assert newer `updated_at` wins; FAQ wins on tie
- Citation: assert `source_id` never leaks into API response

---

## Environment Setup

This project uses **Infisical** for secret management. See [`docs/infisical/setup.md`](./docs/infisical/setup.md) for the full setup guide.

### Pre-commit Hooks

```bash
pip3 install pre-commit
pre-commit install
```

## Dev Commands

```bash
make dev.build && make dev.up.d   # build and start
make dev.migrate                  # run migrations
make dev.dcshell                  # bash in django container
make dev.dshell                   # django shell
make test                         # run full test suite with coverage
make cr                           # recompile requirements after editing *.in files
```

## Adding a Package

Add to the appropriate `config/requirements/*.in` file then run `make cr`.
