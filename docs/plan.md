# QueryMaster Corpus Analysis Plan

## Status

Proposed for review. No implementation phase begins without explicit user
approval. This plan covers corpus analysis only; `docs/specs.md` remains the
product authority.

## Objective

Analyze the local documents under `data/` and generate a local Markdown report
at `output/corpus-analysis.md`. The report combines filesystem/container
inventory with Docling content profiling. It does not create searchable
knowledge.

## Decisions

- Run through Docker and Makefile targets, without requiring Django or
  Infisical secrets.
- Pin Docling to `2.129.0` for the baseline run and record all effective tool
  versions in the report.
- Use Docling for every supported file in this corpus.
- Use Tesseract CLI with English (`iso:en`) and PDF-aware selective OCR.
- Enable accurate table structure extraction and cell matching.
- Disable remote services, external plugins, picture descriptions, chart
  extraction, code enrichment, and formula enrichment.
- Process files sequentially with one reusable converter so failures remain
  isolated and model startup is not repeated for each file.
- Include a technical appendix for every file without extracted text excerpts.
- Keep `data/`, `output/`, and generated reports out of Git.

## Boundaries

Included:

- File discovery, size, hash, format, duplicates, and filename collision
  analysis.
- Lightweight PDF and Office-container validation.
- Docling conversion status, errors, warnings, confidence, timing, pages,
  pictures, tables, and layout-item counts.
- PDF native-text, OCR-only, mixed, and empty page statistics.

Excluded:

- Production ingestion, database models, APIs, Celery tasks, or Django Admin.
- Extracted-text exports or document previews.
- Chunking, token counting, embeddings, embedding cost, retrieval, or
  citations.
- Parser comparison, automatic OCR-engine selection, and full-page OCR.
- Corpus-specific parsing rules based on filenames, brands, or content.

## Report Contract

`output/corpus-analysis.md` contains these sections in this order:

1. **Run configuration** — timestamp, environment, Docling version, Tesseract
   version, model/configuration fingerprints, input path, and elapsed time.
2. **Inventory summary** — document count, total bytes, format and directory
   distributions, and size statistics.
3. **Integrity findings** — empty files, signature mismatches, invalid Office
   ZIP containers, unsafe expansion ratios, unsupported files, and skipped
   entries.
4. **Identity findings** — SHA-256 duplicate groups and collisions between
   normalized lowercase basenames.
5. **Docling summary** — success, partial-success, skipped, and failure counts;
   confidence grades; processing timings; pages, pictures, tables, and layout
   item totals.
6. **PDF/OCR summary** — native-only, OCR-only scan-candidate, mixed, and empty
   page counts plus OCR confidence and OCR-produced cell counts.
7. **Review queue** — every failed, partial, empty, corrupt, low-confidence, or
   otherwise exceptional document with its reason.
8. **Per-file appendix** — relative path, normalized filename, size,
   abbreviated hash, detected format, integrity result, conversion status,
   duration, structural counts, confidence grades, OCR page categories, and
   errors/warnings.

Page categories use Docling text-cell provenance:

- `native-only`: one or more non-OCR cells and no OCR cells.
- `ocr-only scan candidate`: one or more OCR cells and no native cells.
- `mixed`: both native and OCR cells.
- `empty`: no text cells.

The report calls these values observed OCR usage, not proof that OCR was the
only possible extraction method.

## Implementation Phases

### Phase 1 — Reproducible analysis environment

1. Add an analysis-only Docker image with Docling `2.129.0`, Tesseract CLI,
   and English trained data.
2. Download Docling layout/table model artifacts during the image build so a
   corpus run performs no network access.
3. Add Makefile targets to build the image, run checks, and run the analyzer.
4. Exclude `data/` and `output/` from Docker build context and Git tracking.

Completion criteria:

- The image builds through its Makefile target.
- Inside the image, Docling and Tesseract report the expected versions and the
  English language model is available.
- The image can start with no Django services or Infisical secrets.
- Stop and obtain approval before Phase 2.

### Phase 2 — Analyzer and report generator

1. Add one standalone Python command with defaults:
   `--input data`, `--output output/corpus-analysis.md`, and optional
   `--max-files` for a bounded smoke run.
2. Discover files recursively in deterministic relative-path order. Do not
   follow symlinks. Skip hidden entries and `data/certbot/` if it exists.
3. Accept only QueryMaster formats supported by the pinned Docling release:
   PDF, DOCX, XLSX, CSV, PPTX, TXT, and Markdown. Record other files as
   skipped.
4. Calculate SHA-256 while reading each file once for inventory. Validate PDF
   signatures and Office ZIP structure without extracting reportable content.
5. Convert accepted files through one configured `DocumentConverter`, with
   per-document failures returned as results rather than aborting the run.
6. Aggregate the report contract above and replace the output file atomically
   only after rendering completes.
7. Exit nonzero only for analyzer/setup failures. Document-level failures are
   successful analysis findings and remain visible in the report.

Completion criteria:

- A standard-library test covers deterministic discovery, hidden-file
  exclusion, duplicates, lowercase-name collisions, integrity failures, page
  classification, and Markdown escaping.
- The report contains no extracted document text.
- One document failure cannot prevent later documents from being reported.
- Stop and obtain approval before Phase 3.

### Phase 3 — Bounded smoke analysis

1. Run the analyzer against a deterministic three-file subset using
   `--max-files 3`.
2. Confirm model loading, selective OCR, table/picture counts, confidence data,
   failure isolation, and report formatting.
3. Inspect the report for accidental content excerpts or internal absolute
   paths.

Completion criteria:

- The smoke command completes and generates a readable local report.
- The report contains only relative corpus paths and technical metrics.
- Findings are plausible enough to justify the full run.
- Stop and obtain approval before Phase 4.

### Phase 4 — Full corpus analysis

1. Run the analyzer over every supported document under `data/`.
2. Confirm the current inventory baseline of 100 documents: 96 PDF, 3 XLSX,
   and 1 DOCX. Any difference is reported, not silently corrected.
3. Review failures, partial conversions, low-confidence results, scan
   candidates, tables, pictures, duplicate content, and filename collisions.

Completion criteria:

- Every discovered supported file appears exactly once in the appendix.
- Aggregate totals reconcile with the appendix.
- `.DS_Store` and non-document paths are excluded.
- `output/corpus-analysis.md` exists locally and contains no token, chunk, or
  embedding estimates.
- Stop for user review. Do not commit or push without separate approval.

## Verification Commands

All commands introduced by this work must be Makefile targets. The completed
implementation must provide equivalents of:

```bash
make corpus.build
make corpus.test
make corpus.analyze MAX_FILES=3
make corpus.analyze
```

The full run must be repeatable with no source-document modifications and no
network calls after the analysis image has been built.
