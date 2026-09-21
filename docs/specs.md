# QueryMaster Version-Aware RAG Product Specification

## 1. Purpose

QueryMaster publicly answers questions from two knowledge sources that staff
can change at runtime:

- FAQ question-and-answer records maintained through Django Admin.
- Operational documents uploaded by staff.

The system must answer from the current, completely processed knowledge state.
It must prevent partially indexed, superseded, inactive, or deleted evidence
from appearing in new answers. Answers must stream to the user and cite the
human-readable source locations that support them.

This document defines product behavior. It intentionally does not prescribe
the database schema, service boundaries, task topology, or provider-specific
implementation.

## 2. Core Invariants

The following rules are non-negotiable:

1. Exactly one successfully processed version of a logical source is current
   and searchable at a time. A source with no successful current version
   contributes no searchable evidence.
2. A new version becomes searchable only after all required processing has
   completed successfully.
3. The last successful version remains searchable while an update is being
   processed. A failed update never replaces or damages it.
4. Activation and programmatic fallback change the searchable version
   atomically. Users never observe a mixture of versions from one source.
5. New queries use current evidence only. Inactive, failed, superseded, and
   deleted evidence is excluded.
6. Evidence authority is determined by `updated_at`. There is no
   `effective_at` concept in this product.
7. Public responses expose human-readable citations and never expose internal
   source, version, block, chunk, or database identifiers.
8. Query history remains available after its supporting evidence becomes
   inactive or is deleted.
9. Successful source versions and query history are retained indefinitely.

## 3. Users and Authorization

### 3.1 Staff users

Staff users can:

- Create and edit FAQs through Django Admin.
- Upload new documents and updated document versions.
- Inspect ingestion status, warnings, and failures.
- Delete current knowledge through protected staff operations.

Historical fallback is selected programmatically. Staff do not manually pick
an older document version to restore through Django Admin or a version
selector.

### 3.2 Public users

Public users can:

- Ask questions against the current knowledge base without authentication.
- Receive incrementally streamed answers with citations.

Knowledge management and query-log inspection remain protected staff
operations. Public chat access does not grant access to document, FAQ,
ingestion, or query-log administration.

## 4. Terminology

### 4.1 Logical source

A logical source is one FAQ or one logical document.

For documents, the normalized lowercase filename identifies the logical
document. Uploading a different filename creates a different logical document.
The initial release does not automatically merge differently named files.

### 4.2 Version

A version is one submitted state of a logical source. A version may be
processing, successful, failed, current, inactive, or deleted according to its
lifecycle.

### 4.3 Evidence

Evidence is a retrievable piece derived from an FAQ or document. A large FAQ
may produce multiple retrieval pieces while remaining one FAQ and one citation
source.

### 4.4 Current version

The current version is the successful version programmatically selected for
new retrieval. Selection occurs after successful processing, or through
automatic fallback after deletion.

## 5. Goals

### G1. Continuously current knowledge

FAQ and document updates become available without application redeployment. A
new version becomes searchable only after processing succeeds.

### G2. No partially indexed knowledge

Users continue receiving answers from the last successful version while an
update is processing. Parsing, OCR, indexing, or embedding failure leaves the
current version unchanged.

### G3. Latest conflicting evidence wins

When retrieved evidence genuinely conflicts, the evidence with the greater
`updated_at` value is authoritative, including a difference of one
millisecond. FAQ and document evidence follow the same rule.

An exact `updated_at` tie is exceptional. The answer must present the conflict
and ask the user which source applies instead of silently choosing one.

Timestamp comparison applies only to genuinely conflicting evidence.
Complementary evidence remains eligible regardless of timestamp.

### G4. Multi-source answers

Broad questions may require many independent evidence locations, including a
combination such as eight FAQs and two document sections. Retrieval and context
selection must follow relevance and available context rather than a fixed FAQ
to document ratio.

### G5. Traceable citations

Every answer identifies the evidence it used:

- FAQ citations show the FAQ number.
- Document citations show the document name and section.
- When no section exists, the citation uses the best available page, slide,
  sheet and row, paragraph, or line location.
- A claim supported by both an FAQ and a document cites both.

Citation metadata is controlled by the application. The language model may
refer to temporary internal source labels during generation, but those labels
are mapped to trusted source metadata before the response is exposed.

### G6. Programmatic recovery

Deleting a current FAQ or document version triggers automatic fallback to the
most recent prior successfully processed version whose reusable evidence is
still available. Staff do not manually select the fallback.

The fallback becomes current at restoration time, and its authority for
conflict resolution reflects that restoration through `updated_at`. Fallback
can repeat through every retained successful version. If no prior successful
version is available, the logical source contributes no searchable evidence.

### G7. Efficient updates

An update avoids a new embedding-provider call for evidence whose complete
contextualized content is unchanged. Changed content, new content, or changed
context may require new embeddings. Reuse must not weaken retrieval quality or
atomic activation.

Embedding reuse is independent of authority metadata. Reusing a vector does
not prevent the activated or restored evidence from receiving the appropriate
`updated_at` value.

### G8. Supported knowledge formats

The initial release supports:

- FAQ question-and-answer records.
- PDF, including English scanned pages.
- DOCX.
- XLSX.
- CSV.
- PPTX.
- TXT.
- Markdown.

## 6. Required Product Behavior

### 6.1 Document identity and uploads

1. A normalized lowercase filename identifies one logical document.
2. Uploading changed content under the same filename creates a new version.
3. Uploading byte-identical content creates no version, changes no timestamps,
   and performs no indexing work.
4. Uploading a different filename creates a different logical document.
5. The current successful version remains searchable while the new version is
   processing.
6. Staff can inspect processing progress, warnings, and failures.

### 6.2 FAQ lifecycle

1. Staff create and edit FAQs through Django Admin.
2. An FAQ contains one question and one answer.
3. Creating or editing an FAQ begins processing of new searchable knowledge.
4. An edited FAQ replaces the current searchable version only after processing
   succeeds.
5. A failed FAQ update leaves the previous successful version searchable.
6. A large FAQ may yield multiple retrieval pieces, all of which cite the same
   FAQ number.
7. Deleting the current FAQ version automatically activates the most recent
   prior successful version. Repeated deletion continues through retained
   successful versions until none remains.

### 6.3 Processing and activation

1. Submitted versions remain isolated from retrieval during processing.
2. All required extraction, OCR, normalization, evidence preparation, and
   embedding work must finish before activation.
3. Activation switches the source from its previous successful version to the
   new successful version as one atomic operation.
4. Processing warnings remain visible to staff. A warning may coexist with a
   successful version only when usable content remains and the result satisfies
   the product's quality checks.
5. A version with no usable content fails processing and cannot become current.

### 6.4 Deletion and automatic fallback

1. Deletion removes the selected current source version from new retrieval
   immediately.
2. Embeddings belonging to the deleted source version are physically
   deleted.
3. The original source file, version metadata, operational history, and related
   query history are retained indefinitely.
4. Reusable evidence is retained for every successful version unless that
   version itself is deleted.
5. The system automatically selects the most recent prior successful version
   with retained reusable evidence.
6. Fallback activation is atomic and assigns restoration-time authority through
   `updated_at`.
7. A restored version can later be deleted, causing the system to continue
   backward through successful versions until an eligible version is found.
8. If no eligible prior version exists, no version is restored and the logical
   source disappears from current retrieval.
9. Normal product behavior does not manually restore an arbitrary version and
   does not recreate deleted embeddings merely to perform fallback.

### 6.5 Retrieval and evidence resolution

1. Retrieval broadly considers current FAQ and document evidence.
2. Retrieval must provide sufficient recall for questions requiring evidence
   from 7-10 independent locations.
3. Accurate reranking follows broad retrieval.
4. The final evidence set is selected by relevance, independence, and available
   answer context, without a source-type quota.
5. Equivalent evidence is deduplicated without removing independently useful
   support.
6. Complementary evidence is retained when it contributes to the answer.
7. Genuine conflicts are resolved using `updated_at` according to G3.
8. Generation uses only the resolved final evidence set.

### 6.6 Answers, streaming, and citations

1. Public users can submit queries without authentication.
2. Answers stream incrementally.
3. If generation fails after streaming begins, the stream displays a
   user-visible error and marks any partial output as incomplete.
4. Citations are emitted from trusted source metadata and correspond to
   evidence actually used in the answer.
5. Public answer and citation payloads contain no internal knowledge
   identifiers.
6. An exact-timestamp conflict produces an explicit clarification request rather
   than an unsupported resolution.

### 6.7 Query history

1. Every completed or failed query has a durable history record sufficient for
   operational diagnosis.
2. Query history survives source updates, deletion, fallback, application
   restarts, and deployments.
3. A historical query remains readable even when its original evidence is no
   longer current.
4. Historical citations retain the source description that applied when the
   answer was produced.
5. Query history is retained indefinitely.
6. Query-log inspection is a protected staff operation.

### 6.8 Scanned PDFs

1. English scanned PDF pages are processed with OCR.
2. Pages that remain unreadable produce actionable, staff-visible warnings.
3. Readable pages from a partially unreadable document may become searchable
   only when the resulting version passes quality checks.
4. A document containing no usable content fails instead of becoming an empty
   searchable source.

## 7. Non-Goals

The initial release excludes:

- Public document or FAQ management.
- Hard deletion of source files and history through normal APIs or admin
  actions.
- Staff-selected restoration of arbitrary historical document versions.
- Automatic merging of differently named files into one logical document.
- Non-English OCR.
- Guaranteed handwriting recognition.
- Audio or video knowledge sources.
- Image-to-image or cross-modal retrieval.
- Searching multiple embedding spaces simultaneously.
- Runtime embedding-provider switching without rebuilding affected embeddings.
- Combining unrelated FAQ records into one stored knowledge item.
- Exact character-range reconstruction or highlighting within a chunk.
- Guaranteed minimal embedding work after every edit; changed boundaries or
  context may require nearby evidence to be processed again.
- Query decomposition unless evaluation proves it necessary to meet the
  multi-source recall target.

## 8. Product Constraints

- Application operations use the repository's Docker and Makefile workflow.
- Secrets remain managed through Infisical.
- PostgreSQL remains the system of record.
- Source files, version history, and query history survive application restarts
  and deployments.
- Current knowledge is switched atomically.
- Staff-only operations require staff authorization.
- Public chat requires no authentication; knowledge management and query-log
  inspection remain staff-only.
- The initial release uses one configured embedding space at a time.
- Successful version history and query history are retained indefinitely.

## 9. Success Criteria

The initial release succeeds when all of the following are demonstrated:

1. An update never exposes a partially processed version.
2. A failed update leaves the last successful version searchable.
3. Deleted, failed, superseded, and inactive evidence never appears in a new
   answer.
4. Deleting a current FAQ or document version automatically activates the most
   recent eligible stable version, or activates nothing when none exists.
5. Automatic fallback can continue through every retained successful version.
6. Embeddings for the deleted source version are removed.
7. Restored evidence becomes authoritative according to its restoration-time
   `updated_at`.
8. Questions requiring 7-10 FAQ or document locations retrieve and retain the
   necessary evidence.
9. Newer genuinely conflicting evidence wins according to `updated_at`.
10. An exact timestamp tie produces an explicit clarification request.
11. Every citation identifies the correct FAQ or document location.
12. Public responses never expose internal knowledge identifiers.
13. Public users can chat without authentication.
14. A streaming failure displays a user-visible error and marks partial output
    as incomplete.
15. Byte-identical uploads perform no new indexing work and change no
    timestamps.
16. Unchanged contextualized evidence avoids a new embedding-provider call.
17. English scanned PDFs produce searchable text or actionable warnings.
18. Query history persists after its original evidence becomes inactive or is
    deleted.

## 10. Acceptance Scenarios

### 10.1 Successful document update

Given an active policy document, when staff upload changed content using the
same normalized lowercase filename, users continue receiving answers from the
old version until processing succeeds. After atomic activation, new queries use
only the new current version.

### 10.2 Failed document update

Given an active document, when parsing, OCR, or embedding fails for an update,
the new version is shown as failed and the active document remains unchanged.

### 10.3 Byte-identical document upload

Given an existing logical document, when staff upload byte-identical content
under the same normalized filename, no version is created, no timestamp
changes, and no indexing or embedding work occurs.

### 10.4 FAQ update

Given an active FAQ, when staff edit its question or answer, the previous FAQ
version remains searchable until processing succeeds. A failure leaves the
previous FAQ version unchanged.

### 10.5 Multi-source question

Given relevant content across several FAQs and documents, when a user asks a
broad question, the final evidence may contain all relevant source types and
locations that fit the answer context, and the answer cites every source it
uses.

### 10.6 Conflicting evidence

Given two genuinely conflicting pieces of current evidence, when one has a
greater `updated_at`, the answer follows the newer evidence. When their
timestamps are exactly equal, the answer presents the conflict and requests
clarification.

### 10.7 Source deletion with fallback

Given a current FAQ or document with a prior successful version, when staff
delete the current version, its embeddings are deleted and it becomes
non-retrievable. The system atomically selects the most recent eligible stable
version without staff intervention and applies restoration-time authority.

### 10.8 Repeated fallback and exhaustion

Given a source with multiple successful versions, repeated deletion falls back
through each eligible version in newest-to-oldest order. After the final
eligible version is deleted, the logical source contributes no evidence to
subsequent queries.

### 10.9 Scanned PDF with unreadable pages

Given an English scanned PDF containing readable and unreadable pages, when it
is processed, staff can see actionable warnings for unreadable pages. The
version becomes searchable only if usable content remains and quality checks
pass.

### 10.10 Historical query after source deletion

Given a prior answer with citations, when its source version is later deleted,
the historical query and the citation descriptions recorded for that answer
remain in protected staff-accessible query history indefinitely.

## 11. Release Measurements

The implementation plan must define measurable release thresholds for:

- Multi-source retrieval recall.
- Citation correctness and completeness.
- OCR success and warning quality.
- Time to first streamed output and total response latency.
- Ingestion latency and failure recovery.
- Atomic activation and stale-evidence exclusion reliability.

The thresholds must be approved before release evaluation begins.
