# QueryMaster Product Specification

Status: Approved product baseline

Last updated: 2026-09-17

This document defines the problem, product scope, required behavior, and
success criteria. Technical architecture, APIs, database fields, processing
flows, and implementation sequencing belong in [`plan.md`](./plan.md).

## 1. Problem

Organizations answer user questions from two continuously changing knowledge
sources:

- FAQs maintained by staff.
- Operational documents uploaded by staff.

Existing RAG implementations commonly return stale or incomplete answers
because they cannot reliably distinguish current content from replaced
content, updates are visible before indexing finishes, broad questions require
evidence from many independent sources, and citations do not identify where an
answer came from.

QueryMaster must provide answers from the currently selected knowledge while
preserving prior versions for administrative restoration and query history.

## 2. Users

### Staff users

Staff maintain FAQs and documents, inspect ingestion status, delete sources,
and restore historical versions.

### Authenticated users

Authenticated users ask questions, receive streamed answers with citations,
and access their previous queries.

## 3. Goals

### G1. Continuously current knowledge

Updates to FAQs and documents must become available without redeploying the
application. A new version becomes searchable only after its processing has
completed successfully.

### G2. No partially indexed knowledge

Users must continue receiving answers from the last successful version while
an update is processing. Failed updates must not damage or replace searchable
content.

### G3. Latest evidence wins

When retrieved evidence genuinely conflicts, the evidence with the greater
`updated_at` value is authoritative, even if the difference is only one
millisecond and regardless of whether it came from an FAQ or document.

An exact timestamp tie is considered exceptional. The answer must expose the
conflict and ask the user which source applies instead of silently choosing.

### G4. Multi-source answers

The system must support broad questions whose answers require many independent
pieces of evidence, including combinations such as eight FAQs and two document
sections. It must not enforce an equal FAQ/document ratio.

### G5. Traceable citations

Every answer must identify the evidence used:

- FAQ citations identify the FAQ number.
- Document citations identify the document name and section.
- When no section exists, citations use the best available page, slide,
  sheet/row, paragraph, or line location.
- If both an FAQ and document support a claim, both are cited.

Internal source, version, block, and chunk identifiers must not be displayed to
users.

### G6. Recoverable history

Historical source versions, their original files, and previous query logs must
remain stored. Staff must be able to select any successfully processed version
and make it current again without re-uploading the file.

### G7. Efficient updates

Updating a source should avoid recalculating embeddings for evidence whose
contextualized content is unchanged. Efficiency must not compromise retrieval
quality or atomic activation.

### G8. Supported knowledge formats

The initial product supports:

- FAQ question-and-answer records.
- PDF, including English scanned pages.
- DOCX.
- XLSX.
- CSV.
- PPTX.
- TXT.
- Markdown.

## 4. Required Product Behavior

### 4.1 Documents

- A lowercase filename identifies one logical document.
- Uploading the same filename with changed content creates a new version.
- Uploading byte-identical content does not create a version or change
  timestamps.
- A different filename creates a different logical document.
- The previously searchable version remains available while the update is
  processing.
- Staff can inspect processing failures and warnings.

### 4.2 FAQs

- Staff create and edit FAQs through Django Admin.
- An FAQ consists of one question and one answer.
- Editing an FAQ creates new searchable knowledge only after processing
  succeeds.
- An unusually large FAQ may be represented by multiple retrieval pieces but
  remains one FAQ and one citation source.

### 4.3 Deletion

- Deleting a document version permanently removes that version and all its
  embeddings (chunks).
- When a version is deleted, the backend automatically activates the most
  recent previously successful version of the same document, if one exists.
- If no prior successful version exists, the document becomes inactive with
  no searchable content.
- Version lifecycle is managed programmatically by the backend; staff do not
  restore versions manually through admin or any API.

### 4.4 Queries

- Authenticated and anonymous users can query the knowledge base.
- Anonymous queries are recorded with no user association.
- Answers stream incrementally.
- Retrieval considers both FAQs and documents broadly before accurate
  reranking.
- The final evidence set is determined by relevance and available context, not
  a fixed source quota.
- Query history remains available even when its original evidence later becomes
  inactive.

### 4.5 Scanned documents

- English scanned PDF pages are supported.
- Pages that remain unreadable produce visible ingestion warnings.
- A document containing no usable content must fail processing rather than
  becoming an empty searchable source.

## 5. Non-Goals

The initial release does not include:

- Anonymous querying.
- Public document or FAQ management.
- Manual version restoration by staff through admin or API.
- Automatic merging of differently named files as one document.
- Non-English OCR.
- Handwriting recognition guarantees.
- Audio or video knowledge sources.
- Image-to-image or cross-modal retrieval.
- Searching multiple embedding spaces simultaneously.
- Runtime embedding-provider switching without rebuilding embeddings.
- Combining unrelated FAQ records into one stored knowledge item.
- Exact reconstruction or highlighting of character ranges inside a chunk.
- Guaranteed minimal embedding work after every edit; exact reusable content is
  reused, but changed boundaries may require nearby content to be processed
  again.
- Query decomposition in the first release unless evaluation proves it is
  required to meet multi-source recall goals.

## 6. Product Constraints

- Application operations run through the existing Docker and Makefile
  workflow.
- Secrets remain managed through Infisical.
- PostgreSQL remains the system of record.
- Current knowledge must be switchable atomically.
- Staff-only operations must remain protected by staff authorization.
- Users may access only query records they own unless they are staff.

## 7. Success Criteria

The first release is successful when:

1. Updating a source never exposes a partially processed version.
2. A failed update leaves the last successful version searchable.
3. Deleted and inactive content never appears in a new answer.
4. Deleting a version permanently removes its embeddings and automatically
   activates the previous successful version if one exists.
5. When no prior version exists after deletion, the document has no active
   searchable content.
6. Questions requiring evidence from 7–10 FAQ/document locations retrieve and
   retain the necessary evidence.
7. Newer conflicting evidence wins according to `updated_at`.
8. Exact timestamp ties produce an explicit clarification request.
9. Every answer citation identifies the correct FAQ or document location.
10. Public responses never expose internal knowledge identifiers.
11. Byte-identical uploads perform no new indexing work.
12. Unchanged contextualized evidence avoids a new embedding-provider call.
13. English scanned PDFs produce searchable text or actionable warnings.
14. Query history persists after its evidence becomes inactive.

## 8. Acceptance Scenarios

### Successful document update

Given an active policy document, when staff upload changed content using the
same lowercase filename, users continue receiving answers from the old version
until processing succeeds. After activation, new queries use only the selected
new version.

### Failed document update

Given an active document, when parsing, OCR, or embedding fails for an update,
the update is shown as failed and the active document remains unchanged.

### Multi-source question

Given relevant content across several FAQs and documents, when a user asks a
broad question, the system may use all relevant sources within its answer
context and cites each source it used.

### Conflicting evidence

Given two conflicting pieces of evidence, when one has a greater `updated_at`,
the answer follows the newer evidence. When their timestamps are equal, the
answer presents the conflict and asks for clarification.

### Version deletion with fallback

Given a document with two successful versions where v2 is active, when v2 is
deleted, its embeddings are permanently removed and v1 automatically becomes
active. Queries immediately use v1's content.

### Version deletion with no fallback

Given a document with only one successful version, when that version is deleted,
its embeddings are permanently removed and the document has no active searchable
content. It no longer appears in any query results.

