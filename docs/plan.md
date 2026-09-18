# QueryMaster Technical Design and Implementation Plan

This document is the implementation source of truth for the product behavior
defined in [`specs.md`](./specs.md). The ERD is at
[`querymaster_erd.drawio`](./querymaster_erd.drawio).

Last updated: 2026-09-17

## 1. Architecture Overview

```text
FAQ / uploaded document
        ↓
Document → DocumentRevision
FAQ (title + question + answer)
        ↓
parse → normalize → chunks → contextual embed
        ↓
atomic activation (Chunk.is_active flip)

User query (anonymous, session-keyed)
        ↓
embed query (RETRIEVAL_QUERY)
        ↓
hybrid search: pgvector ANN (HNSW) + Postgres BM25 full-text
        ↓
Reciprocal Rank Fusion → deduplicate → LLM rerank
        ↓
updated_at conflict resolution
        ↓
context selection → streamed SSE answer → citations
```

## 2. Django App Layout

Three new apps replace the placeholder `querymaster/ai/`:

```text
querymaster/
  documents/              — Document, DocumentRevision models + upload API
    models.py
    admin.py
    services/
      ingestion.py        — parse, diff, Celery dispatch
      activation.py       — atomic revision activation
      deletion.py         — version deletion + chunk purge + fallback activation
    api/v1/
      views.py
      serializers.py
      urls.py

  faqs/                   — FAQ model + admin
    models.py
    admin.py
    services/
      ingestion.py        — FAQ chunk rebuild on edit

  knowledge/              — Chunk, ChatSession, QueryLog + pipeline
    models.py
    admin.py
    providers/
      embedding/
        base.py           — EmbeddingProvider protocol
        gemini.py
        openai.py
      llm/
        base.py           — LLMProvider protocol
        gemini.py
        openai.py
      reranker/
        base.py           — RerankerProvider protocol
        gemini.py
    parsers/
      base.py
      pdf.py              — PyMuPDF + PaddleOCR fallback
      docx.py
      spreadsheet.py      — XLSX + CSV
      presentation.py     — PPTX
      text.py             — TXT + Markdown
    utils/
      normalization.py
      hashing.py
      chunking.py         — sentence-aware packing
      rrf.py              — Reciprocal Rank Fusion
      context.py          — contextual embedding input builder
    nodes/
      retrieve.py         — hybrid search
      rerank.py           — LLM reranker
      deduplicate.py      — content-hash dedup
      resolve.py          — updated_at conflict resolution
      generate.py         — streaming LLM call
    graphs/
      query_graph.py      — LangGraph StateGraph
    tasks.py              — Celery ingestion tasks
    api/v1/
      views.py            — query SSE endpoint + session lifecycle
      serializers.py
      urls.py
```

Register all three apps in `CUSTOM_APPS` in `config/settings/base.py` and
prefix their URLs in `config/urls.py`:

```text
/api/v1/documents/   → querymaster.documents.api.v1.urls
/api/v1/faqs/        → querymaster.faqs.api.v1.urls
/api/v1/knowledge/   → querymaster.knowledge.api.v1.urls
```

## 3. Dependencies and Configuration

Add packages to `config/requirements/*.in`, then run `make cr`:

- `pgvector` — Python bindings for the Postgres pgvector extension
- `google-genai` — Google GenAI SDK (Gemini embedding + LLM)
- `openai` — OpenAI SDK (optional embedding + LLM)
- `pymupdf` — PDF text extraction
- `paddlepaddle` (CPU) and `paddleocr` — English OCR for scanned pages
- `python-docx`, `openpyxl`, `python-pptx` — DOCX / XLSX / PPTX
- `tiktoken` — deterministic token counting
- `langchain-core`, `langgraph` — query orchestration

Bake PaddleOCR model assets into the Django/Celery Docker image. Workers
must not download models at runtime.

### Runtime configuration (django-constance)

```text
EMBEDDING_PROVIDER=gemini
EMBEDDING_MODEL=gemini-embedding-001
EMBEDDING_DIMENSION=768

LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash

VECTOR_CANDIDATE_LIMIT=100
KEYWORD_CANDIDATE_LIMIT=100
RERANK_TOP_K=20
GENERATION_CONTEXT_TOKEN_LIMIT=8000
```

Retrieval limits are constance values, not hard-coded constants. All
provider credentials live in Infisical.

## 4. Data Model

All models use `django_extensions.TimeStampedModel` for `created`/`modified`
and `ActivatorModel` for soft-delete via `status`/`activate_date`/`deactivate_date`
unless noted otherwise.

### `Document`

App: `querymaster.documents`

| Field | Type | Notes |
|---|---|---|
| `id` | `BigAutoField` | Primary key |
| `title` | `CharField` | Display name |
| `filename` | `CharField(unique=True)` | Lowercase; document identity key |
| `file` | `FileField` | Current upload (S3) |
| `created` | `DateTimeField` | From TimeStampedModel |
| `modified` | `DateTimeField` | From TimeStampedModel |
| `status` | `IntegerField` | From ActivatorModel (ACTIVE/INACTIVE) |
| `activate_date` | `DateTimeField` | From ActivatorModel |
| `deactivate_date` | `DateTimeField` | From ActivatorModel |

### `DocumentRevision`

App: `querymaster.documents`

| Field | Type | Notes |
|---|---|---|
| `id` | `BigAutoField` | Primary key |
| `document` | `ForeignKey(Document, PROTECT)` | Parent document |
| `version` | `PositiveIntegerField` | Sequential per document |
| `ingestion_status` | `CharField` | `pending`, `processing`, `succeeded`, `failed` |
| `file_hash` | `CharField(64)` | SHA-256; detects byte-identical uploads |
| `parse_warnings` | `JSONField` | Default list; OCR warnings etc. |
| `failure_reason` | `TextField` | Blank by default |
| `embedding_provider` | `CharField` | `gemini` or `openai` |
| `embedding_model` | `CharField` | Model ID at ingestion time |
| `created` | `DateTimeField` | From TimeStampedModel |
| `modified` | `DateTimeField` | From TimeStampedModel |
| `status` | `IntegerField` | From ActivatorModel |
| `activate_date` | `DateTimeField` | From ActivatorModel |
| `deactivate_date` | `DateTimeField` | From ActivatorModel |

Unique `(document, version)`. Only `succeeded` revisions may be activated.

### `FAQ`

App: `querymaster.faqs`

| Field | Type | Notes |
|---|---|---|
| `id` | `BigAutoField` | Also the public FAQ number in citations |
| `title` | `CharField` | Short human label |
| `question` | `TextField` | Embedded together with answer |
| `answer` | `TextField` | Embedded together with question |
| `content_hash` | `CharField(64)` | SHA-256 of normalized question+answer |
| `content_updated_at` | `DateTimeField` | Last content change; authority timestamp |
| `created` | `DateTimeField` | From TimeStampedModel |
| `modified` | `DateTimeField` | From TimeStampedModel |
| `status` | `IntegerField` | From ActivatorModel |
| `activate_date` | `DateTimeField` | From ActivatorModel |
| `deactivate_date` | `DateTimeField` | From ActivatorModel |

Editing the FAQ question or answer triggers a new Celery chunk-rebuild task.
`content_hash` detects no-op edits (formatting-only saves bypass the task).

### `Chunk` (unified)

App: `querymaster.knowledge`

One table covers both document chunks and FAQ chunks. The source is
identified by a Django `ContentType` GenericForeignKey pointing to either
`DocumentRevision` (document chunks) or `FAQ` (FAQ chunks).

| Field | Type | Notes |
|---|---|---|
| `id` | `BigAutoField` | Primary key |
| `content_type` | `ForeignKey(ContentType)` | `DocumentRevision` or `FAQ` |
| `object_id` | `PositiveIntegerField` | PK of the source row |
| `heading` | `CharField(null=True)` | Section heading; null for FAQs and flat docs |
| `page_number` | `IntegerField(null=True)` | For PDF/PPTX citations; null for FAQs |
| `position` | `IntegerField(null=True)` | Slide/sheet row range; null when N/A |
| `chunk_index` | `PositiveIntegerField` | Zero-based order within the source |
| `text` | `TextField` | Evidence text sent to generation |
| `embedding` | `VectorField(768)` | L2-normalized cosine vector |
| `is_active` | `BooleanField` | True only for the current active revision/FAQ |
| `content_hash` | `CharField(64)` | SHA-256 of normalized text + contextual prefix |
| `content_updated_at` | `DateTimeField` | Authority timestamp for conflict resolution |

Unique `(content_type, object_id, chunk_index)`.

Indexes:
- `HNSW` cosine index on `embedding` — single ANN search covers all sources
- `GIN` index on `to_tsvector(text)` — BM25 full-text search
- `B-tree` on `is_active` — O(1) retrieval filter
- `B-tree` on `content_hash` — O(1) diff and reuse lookups
- `B-tree` on `content_updated_at` — conflict resolution ordering

**Embedding reuse:** build a hash set of existing `content_hash` values for
the previous revision. For each new chunk, check the set — O(1) per chunk.
Matches copy the old vector and `content_updated_at`; mismatches call the
embedding provider. This replaces any block-level pre-filtering layer.

### `ChatSession`

App: `querymaster.knowledge`

Created by the backend when a user opens the chat tab. The UUID is returned
to the frontend and held in memory (not persisted client-side). The session
has no user foreign key — all queries are anonymous.

| Field | Type | Notes |
|---|---|---|
| `id` | `UUIDField(primary_key=True)` | Backend-generated UUID |
| `ended_at` | `DateTimeField(null=True)` | Set via PATCH on tab close (best-effort) |
| `created` | `DateTimeField` | From TimeStampedModel |
| `modified` | `DateTimeField` | From TimeStampedModel |

### `QueryLog`

App: `querymaster.knowledge`

| Field | Type | Notes |
|---|---|---|
| `id` | `BigAutoField` | Primary key |
| `session` | `ForeignKey(ChatSession, PROTECT)` | Parent session |
| `query` | `TextField` | Original user input |
| `answer` | `TextField` | Accumulated final answer |
| `citations` | `JSONField` | Public citation payload |
| `created` | `DateTimeField` | From TimeStampedModel |
| `modified` | `DateTimeField` | From TimeStampedModel |

## 5. Parsing, Normalization, and Chunking

### Normalization

Unicode normalization (NFC), line-ending normalization, formatting-only
whitespace collapse, trimming, meaningful paragraph retention, and
deterministic table serialization. Preserve case, punctuation, and numbers.

### Parsing rules by format

| Format | Unit parsed as | Notes |
|---|---|---|
| PDF | Heading sections; page fallback | Scanned pages → PaddleOCR English; fail whole doc if fully unreadable |
| DOCX / TXT / MD | Heading sections; paragraph fallback | |
| PPTX | One slide | Include title/body/table text; exclude speaker notes |
| XLSX / CSV | Sheet header + contiguous row groups | First line of each block is the sheet header |
| FAQ | Full question + answer | One or more chunks depending on token length |

### Chunking

- Sentence-aware sequential packing.
- Target 400 tokens, maximum 512 tokens, zero overlap.
- Split by tokens only when one sentence exceeds 512 tokens.
- Preserve order with `chunk_index`.

### Contextual embedding prefix (Anthropic's Contextual Retrieval)

Before embedding, prepend a 50–100 token context string to each chunk's
text. This is the `content_hash` input and the embedded text; `Chunk.text`
stores the raw chunk without the prefix.

| Format | Context prefix |
|---|---|
| PDF/DOCX/TXT/MD | `Document: {title}. Section: {heading}.` |
| PPTX | `Document: {title}. Slide {n}: {slide_title}.` |
| XLSX/CSV | `Document: {title}. Sheet: {sheet}. Rows {start}–{end}.` |
| FAQ | `FAQ #{id}: {question}` (prepended to the answer chunk) |

## 6. Embedding Implementation

```text
provider:    gemini
model:       gemini-embedding-001
dimensions:  768
doc task:    RETRIEVAL_DOCUMENT
query task:  RETRIEVAL_QUERY
normalization: L2
distance:    cosine
index:       HNSW
```

- Define `EmbeddingProvider` protocol; implement Gemini first, OpenAI second.
- Validate every response: exactly 768 finite values.
- L2-normalize before persistence.
- Batch requests (max 20 chunks per call).
- Retry only transient provider errors with exponential backoff.
- A provider/model change invalidates all existing vectors; a management
  command triggers a full re-index.

## 7. Ingestion Flow

### Document upload

1. Validate staff access, file extension, MIME type, and size.
2. Lowercase the basename; find or create `Document`.
3. Stream SHA-256 without loading the full file into memory.
4. If the active revision has the same `file_hash`, return `unchanged`.
5. Create a new `DocumentRevision` with `ingestion_status=pending`.
6. Dispatch Celery ingestion chord; return `202 Accepted`.

### Celery chord

```text
parse_revision_task
    ↓
compute chunks; build content_hash set from previous active revision
    ↓
O(1) per chunk: hash match → copy vector; miss → queue embed
    ↓
group(embed_chunk_batch_task × N)   ← fan-out, 20 chunks per batch
    ↓ chord callback
activate_revision_task
```

- Parse task writes only to the new revision; current knowledge is untouched.
- Embed tasks are idempotent; retried tasks skip already-embedded chunks.
- Permanent failure records `failure_reason` and leaves the current revision active.

### Atomic activation

Inside one Postgres transaction with `select_for_update()` on `Document`:

1. Verify every new-revision chunk has a valid 768-dim vector.
2. Set `Chunk.is_active = False` for all chunks belonging to the previous
   active revision.
3. Set `Chunk.is_active = True` for all chunks of the new revision.
4. Set `DocumentRevision.ingestion_status = succeeded`.
5. Soft-deactivate the previous revision via `ActivatorModel.status = INACTIVE`.
6. Activate the new revision via `ActivatorModel.status = ACTIVE`.
7. Update `Document.modified` to now.
8. Commit.

New chunks get `content_updated_at = now()`. Reused chunks retain their
copied `content_updated_at`.

### FAQ ingestion

Triggered automatically on `FAQ` save when `content_hash` changes:

1. Compute new `content_hash` for the edited question + answer.
2. If unchanged, skip.
3. Set `FAQ.status = INACTIVE` (soft-deactivate) and dispatch
   `rebuild_faq_chunks_task`.
4. Task: delete existing `Chunk` rows for this FAQ, reparse and re-embed,
   then reactivate (`FAQ.status = ACTIVE`) and set `content_updated_at = now()`.
5. All `Chunk.is_active` for this FAQ flip in the same transaction.

### Version deletion

Inside one transaction with `select_for_update()` on `Document`:

1. Permanently delete all `Chunk` rows belonging to the revision being deleted.
2. Delete the `DocumentRevision` row itself.
3. Query for the most recent prior revision with `ingestion_status=succeeded`.
4. If one exists: set its chunks `is_active = True`, flip its
   `ActivatorModel.status = ACTIVE`, update `Document.modified` to now.
5. If none exists: the document has no active content — no chunks are active.

## 8. Query Pipeline (LangGraph)

```text
ChatSession.id (UUID) supplied by frontend on every request
        ↓
expand node      — HyDE: embed a synthetic answer to expand recall
        ↓
retrieve node    — hybrid search (vector ANN + BM25 full-text), RRF merge
        ↓
rerank node      — LLM reranker (Gemini structured output)
        ↓
deduplicate node — drop chunks with identical content_hash
        ↓
resolve node     — updated_at conflict resolution
        ↓
generate node    — streaming SSE; persist QueryLog
```

### Session lifecycle

- `POST /api/v1/knowledge/sessions/` → backend creates `ChatSession`, returns UUID.
- Frontend holds UUID in memory for the tab lifetime.
- Every query request includes the UUID.
- `PATCH /api/v1/knowledge/sessions/{id}/` with `{"ended_at": "<iso>"}` on tab
  close (best-effort via `beforeunload`).

### Broad retrieval

1. Embed the query with `RETRIEVAL_QUERY` and the active embedding profile.
2. Optionally generate a hypothetical answer (HyDE) for a second query vector.
3. Run cosine ANN over `Chunk` where `is_active = True`.
4. Run Postgres BM25 full-text over the same eligible rows.
5. Merge with Reciprocal Rank Fusion:

```text
RRF(d) = Σ 1 / (k + rank_i(d))   where k = 60
```

6. Deduplicate identical `content_hash` values, retaining highest rank.

### LLM reranking and context selection

- Send query + top `RERANK_TOP_K` candidates to the Gemini reranker.
- Require structured output: candidate ID and relevance score.
- Select by relevance threshold and `GENERATION_CONTEXT_TOKEN_LIMIT`.
- No source-type quota: 8 FAQs and 2 document sections is a valid selection.

### Conflict resolution

- Detect genuine contradictory claims among the selected candidates.
- The strictly greater `Chunk.content_updated_at` wins regardless of source type.
- On an exact tie, preserve both candidates and instruct generation to expose
  the conflict and ask the user which source applies.

### Generation and streaming

- Build context from selected chunks within the token budget.
- Label evidence with prompt-local references (not internal IDs).
- Instruct the LLM to answer only from supplied evidence and associate each
  claim with its reference.
- Stream SSE:

```text
event: token       data: {"text":"..."}
event: citations   data: {"citations":[...]}
event: done        data: {}
event: error       data: {"message":"..."}
```

- Create `QueryLog` at stream start; update `answer` and `citations` on done.

## 9. API Design

All responses follow the existing DRF error conventions.

### Session lifecycle

```text
POST   /api/v1/knowledge/sessions/            → create ChatSession, return UUID
PATCH  /api/v1/knowledge/sessions/{id}/       → set ended_at
```

### Query

```text
POST   /api/v1/knowledge/query/               → SSE stream (session UUID in body)
GET    /api/v1/knowledge/query/{id}/          → QueryLog detail (staff only)
```

`POST /api/v1/knowledge/query/` body:

```json
{"session": "uuid", "query": "What are the refund rules?"}
```

Response: `text/event-stream` as above.

### Documents

```text
POST   /api/v1/documents/upload/                      → staff; multipart: file, title?
GET    /api/v1/documents/                             → staff; paginated list
GET    /api/v1/documents/{id}/status/                 → staff; current + latest revision
DELETE /api/v1/documents/{id}/revisions/{rev_id}/    → staff; hard delete revision (204)
```

Upload responses:
- `201`: new document queued.
- `202`: existing document update queued.
- `200`: byte-identical, `status=unchanged`.
- `400`: invalid/unsupported file.

### FAQs

```text
GET    /api/v1/faqs/                          → staff + authenticated; list active FAQs
```

FAQ creation and editing are Django Admin only.

## 10. Citations

Public citations never include source, revision, or chunk IDs.

**FAQ:**
```json
{"source_type": "faq", "faq_number": 12, "title": "Returns policy"}
```

**Document:**
```json
{
  "source_type": "document",
  "document_name": "refund-policy.pdf",
  "section": "Refund processing time",
  "page_start": 4,
  "page_end": 5
}
```

Use slide number or sheet/row range when `page_number` is null. Emit
separate citations when both an FAQ and a document support a claim.
Deduplicate at FAQ or document-section level.

## 11. Admin

**DocumentAdmin:**
- Columns: filename, title, active revision, ingestion status, created, modified.
- Inline: `DocumentRevision` with ingestion status, warnings, failure reason,
  and a restore action per successful revision.
- Actions: soft delete, restore selected revision.

**FAQAdmin:**
- Columns: title, category, question preview, status, chunk count, content_updated_at.
- Inline: category selector.
- All lifecycle changes call services; admin code does not duplicate ingestion logic.

Make historical revision data and raw chunk text read-only in admin.

## 12. Security, Reliability, and Observability

- Staff permission on all document mutation and inspection endpoints.
- No authentication requirement on query endpoints (anonymous session-keyed).
- Validate file extension, MIME type, and upload size before any parsing.
- Sanitize filenames; never use uploaded paths in shell or OS calls.
- Treat all source text as untrusted prompt content; delimit it from system
  instructions in LLM calls.
- Bound: OCR page count, parser memory, chunk count per revision, embedding
  batch size, Celery retry count, ANN and BM25 candidate pools, context tokens.
- Log: correlation ID, session ID, source/revision IDs, task ID, timings,
  chunk reuse counts, OCR pages processed, provider token usage, failure reason.
- Metrics: ingestion duration, OCR rate, embedding calls vs. reuse,
  failed revision count, vector/keyword search latency, rerank latency,
  first-token latency.

## 13. Implementation Sequence

### Phase 1: Infrastructure and models

Add all dependencies; enable pgvector extension migration; create all models
(`Document`, `DocumentRevision`, `FAQ`, `Chunk`, `ChatSession`, `QueryLog`)
with constraints and indexes; register apps and URL prefixes; basic admin
registration.

Done when: clean migration and rollback succeed; model constraint tests pass.

### Phase 2: Parsing and chunking

Implement normalization, hashing, all parsers, contextual prefix builder, and
sentence-aware chunking.

Done when: golden-file tests pass for all formats (scanned/mixed PDFs, empty
docs, heading sections, slides, tables, row groups).

### Phase 3: Embedding and ingestion

Implement Gemini embedding provider, O(1) hash-based reuse, Celery
parse→embed(fan-out)→activate chord, idempotent embed tasks, failure
handling, and atomic activation transaction.

Done when: unchanged content makes zero provider calls; failed updates leave
the active revision intact; concurrent uploads serialize correctly.

### Phase 4: FAQ ingestion

Implement FAQ save signal handler, `rebuild_faq_chunks_task`, and atomic
`is_active` flip.

Done when: FAQ edit triggers chunk rebuild; formatting-only saves are ignored;
old FAQ chunks are never active during rebuild.

### Phase 5: Document API and admin lifecycle

Implement upload, list, status, and revision deletion endpoints.
All permissions enforced.

Done when: revision deletion permanently removes chunks and activates the
previous version atomically; deletion with no prior version leaves no active
content.

### Phase 6: Retrieval and reranking

Implement vector search, BM25 full-text, RRF, deduplication, Gemini reranker,
context selection, `updated_at` conflict resolution.

Done when: multi-source evaluation retrieves 7–10 required evidence items;
inactive content never appears in results.

### Phase 7: Streaming generation and citations

Implement LangGraph query graph, SSE view, session lifecycle endpoints,
citation builder, QueryLog persistence, and failure states.

Done when: SSE contract, session UUID flow, citation provenance, and
internal-ID non-disclosure tests all pass.

### Phase 8: Evaluation and hardening

Tune retrieval and reranking on representative questions; load-test ingestion
and query concurrency; complete operational dashboards and re-index runbook.

Done when: agreed recall, citation accuracy, latency, and reliability
thresholds pass in repeatable Docker tests.

## 14. Mandatory Test Matrix

**Ingestion — documents:**
- New upload, byte-identical upload (no new version), changed content.
- Failed parse, failed embed, concurrent uploads for the same filename.
- Unchanged chunks reuse embeddings; changed chunks get new `content_updated_at`.
- Active revision stays live throughout a processing revision.
- Failed revision leaves the active revision intact.
- Revision deletion: chunks permanently removed; previous successful revision activates.
- Revision deletion with no prior version: document has no active content.

**Ingestion — FAQs:**
- Edit triggers rebuild; formatting-only save skips rebuild.
- Oversized FAQ produces multiple chunks; normal FAQ produces one.
- Old FAQ chunks never active during rebuild.

**Parsing:**
- All seven supported formats.
- Text PDF, scanned-page PDF, mixed PDF, fully unreadable PDF.
- Heading sections, paragraph fallback, slide blocks, row-group blocks.

**Retrieval:**
- Vector-only, keyword-only, and hybrid wins.
- Question requiring 8 FAQ and 2 document evidence items (multi-source recall).
- Deleted/inactive/processing content never in results.
- Newer FAQ wins, newer document wins, exact timestamp tie asks user.

**Citations:**
- Public payload never contains source, revision, or chunk IDs.
- Correct FAQ number, document name, and section/page in every response.

**Streaming:**
- Complete SSE sequence: token → citations → done.
- Client disconnect handled gracefully.
- Provider failure emits `error` event; `QueryLog` records failure.
- Malformed reranker output rejected without crashing.

**Sessions:**
- Session created on POST, UUID returned.
- `ended_at` set on PATCH.
- QueryLog rows correctly linked to session.

**Security:**
- Non-staff rejected on document endpoints.
- Internal IDs never exposed in query responses.

## 15. Technical Definition of Done

Implementation is complete when every success criterion in `docs/specs.md`
maps to an automated test, all mandatory matrix cases pass inside Docker,
migrations are reversible, inactive-source leakage in retrieval is zero,
and the operational full-reindex procedure is documented and exercised.
