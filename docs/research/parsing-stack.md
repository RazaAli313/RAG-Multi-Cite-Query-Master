# General Document Parsing Stack Research

Status: research recommendation, not an implementation plan or approved
architecture.

This note evaluates a general-purpose parsing stack for QueryMaster's supported
formats. The recommendation is intentionally independent of the documents
currently present in `data/`.

## Recommendation

Use a **hybrid, adapter-based parsing layer** that produces one
application-owned canonical document representation:

| Format | Primary parser | Optional fallback or remediation |
| --- | --- | --- |
| PDF, including English scans | Docling with selective English OCR and table structure enabled | OCRmyPDF plus Tesseract for difficult scans, then parse the repaired PDF again |
| DOCX | `python-docx` | Docling only if evaluation proves it recovers required content the native adapter misses |
| XLSX | `openpyxl` in read-only mode where possible | Docling only for an explicitly tested exceptional case |
| CSV | Python standard-library `csv` | None; fail with actionable dialect or encoding diagnostics |
| PPTX | `python-pptx` | Docling only if evaluation proves it improves unsupported structures |
| TXT | Python text decoding and line iteration | Encoding detection under a strict, recorded policy |
| Markdown | `markdown-it-py` token stream | Plain-text recovery only as an explicit degraded result |

Docling should remain available behind the same parser interface for every
supported format, but it should not automatically become the source of truth
for all formats. The native adapters expose the human locations required by the
product—sheet and row, slide, paragraph, and line—more directly and with less
work than a model-backed universal conversion pipeline. Docling is most valuable
for PDFs, where layout, reading order, tables, and OCR make native extraction
substantially harder.

This is not a set of hard-coded document rules. Dispatch is by validated file
type, and each adapter handles arbitrary valid documents of that type.

## Why the application must own the output contract

No third-party parser's Markdown output should be the canonical record. The
parser layer should emit ordered semantic blocks with, at minimum:

- normalized text or structured table cells;
- block type, such as heading, paragraph, list item, table, caption, or note;
- heading ancestry and stable document order;
- source location appropriate to the format;
- extraction method (`native` or `ocr`) and confidence when available;
- warnings attached to the smallest useful scope;
- parser name, parser version, model/artifact versions, and effective options.

The original structured parser result may also be retained for diagnostics, but
embedding input should be generated from the application-owned blocks. This
separation allows parser libraries to be upgraded without changing retrieval,
chunking, citation, or version lifecycle code.

Stable evidence reuse must hash the complete normalized, contextualized block
content, not parser-internal IDs or raw Markdown. Parser and normalization
versions must be part of the reproducibility record; a parser upgrade can change
reading order or table structure even when the uploaded bytes do not change.

## Docling assessment

Docling supports PDF, DOCX, XLSX, PPTX, Markdown, CSV, plain text, and other
formats, and converts them to a unified `DoclingDocument`. Its PDF pipeline
includes page layout, reading order, table structure, OCR, and lossless JSON
export. It can execute locally, including in air-gapped environments. These are
strong reasons to select it for PDF and to keep it as the universal comparison
engine during evaluation. See the [Docling project](https://github.com/docling-project/docling)
and its [supported formats](https://github.com/docling-project/docling/blob/main/docs/usage/supported_formats.md).

`DoclingDocument` preserves document hierarchy and structured items rather than
only rendered text. Its provenance objects can carry page number, bounding box,
and character spans. That is useful for page citations and diagnostics, but the
QueryMaster adapter must still preserve format-native locations such as sheet
and row or slide number. See the [Docling document model](https://docling-project.github.io/docling/concepts/docling_document/)
and [model reference](https://docling-project.github.io/docling/reference/docling_document/).

For tables, Docling provides TableFormer-based structure extraction with fast
and accurate modes and cell matching. The accurate mode is the appropriate
candidate for complex production PDFs, subject to measured latency and recall.
See [Docling pipeline options](https://docling-project.github.io/docling/reference/pipeline_options/).

For OCR, Docling can use RapidOCR, EasyOCR, Tesseract, and other engines. The PDF
adapter should first use embedded text and invoke English OCR only for pages or
regions that lack usable text. Whole-document OCR should not be the default,
because it increases latency and can replace good native text with OCR errors.
See [OCR in Docling](https://docling-project.github.io/docling/concepts/OCR/).

Operationally, models should be pinned and prefetched into the image or a
controlled model volume. Ingestion must not depend on downloading mutable model
artifacts at runtime. Docling supports CPU and hardware acceleration, but the
release baseline should be benchmarked on the actual production CPU allocation;
GPU acceleration can remain an optimization. See Docling's
[accelerator example](https://docling-project.github.io/docling/_generated/examples/run_with_accelerator/)
and [advanced options](https://docling-project.github.io/docling/usage/advanced_options/).

Docling code is MIT licensed, but its own repository states that individual
models retain their original licenses. Every pinned model artifact therefore
needs a separate license and checksum review. The current Docling model package
also has its own model-card license metadata; do not infer model licensing from
the Python package license.

## Format-native adapters

### DOCX: `python-docx`

`python-docx` exposes paragraphs, runs, styles, tables, headers, and footers.
Paragraph styles can identify headings, and block-level paragraph/table
iteration can retain document order. Its table API also exposes merged and
nested table behavior that a canonical adapter must normalize deliberately.
See the official [python-docx documentation](https://python-docx.readthedocs.io/en/stable/),
[style documentation](https://python-docx.readthedocs.io/en/stable/user/styles-using.html),
and [table guidance](https://python-docx.readthedocs.io/en/latest/user/tables.html).

Recommended locations are section/heading path plus paragraph ordinal, or table
ordinal and row. DOCX does not contain a reliable semantic page number: page
layout depends on the renderer, fonts, and environment. Do not invent page
citations from DOCX XML.

Tracked changes, text boxes, SmartArt, drawings, embedded objects, and unusual
field structures require fixtures and explicit warning behavior. A successful
parse must not silently imply that every visual object was understood.

`python-docx` is MIT licensed according to its
[official license](https://github.com/python-openxml/python-docx/blob/main/LICENSE).

### XLSX: `openpyxl`

`openpyxl` exposes workbook, worksheet, row, cell coordinate, merged-cell, and
formula structures directly. The canonical location should always retain
workbook filename, sheet name, and row or cell range. Row-oriented evidence
should repeat the relevant header context so that a value remains meaningful
after chunking.

Use read-only mode for large workbooks when compatible with the information the
adapter needs; the official documentation describes near-constant memory use.
Read-only mode relies on the workbook's declared dimensions, so incorrect
dimensions must be detected and surfaced rather than silently truncating data.
See [openpyxl optimized modes](https://openpyxl.readthedocs.io/en/stable/optimized.html).

Formula handling must be explicit. With `data_only=False`, cells expose
formulas; with `data_only=True`, they expose the value last cached by Excel, not
a value calculated by openpyxl. Preserve the formula and cached value when
available, warn when a formula has no cached result, and never claim that
openpyxl recalculated a workbook. See the official
[`load_workbook` behavior](https://openpyxl.readthedocs.io/en/stable/api/openpyxl.reader.excel.html).

### CSV: Python `csv`

The standard-library `csv` parser supports dialects, quoted fields, rows that
span physical lines, and streaming iteration. `Sniffer` is only a heuristic and
the Python documentation explicitly says that its header detection can produce
false positives and negatives. The adapter should constrain allowed delimiters,
record the selected dialect and encoding, and warn or fail on ambiguity instead
of silently guessing. Preserve logical record number and the parser's physical
line number for citations. See the [Python `csv` documentation](https://docs.python.org/3/library/csv.html).

### PPTX: `python-pptx`

`python-pptx` exposes slides, shapes, text frames, paragraphs, runs, tables, and
charts. It also exposes shape coordinates, which can be used to impose a
deterministic visual ordering when XML order is insufficient. Group shapes are
recursive, so the adapter must traverse them recursively. See the official
[text documentation](https://python-pptx.readthedocs.io/en/latest/user/text.html)
and [shape API](https://python-pptx.readthedocs.io/en/latest/api/shapes.html).

The canonical location should retain slide number and, where useful, shape and
table-row ordinals. Speaker notes should be a separately typed block so product
policy can decide whether notes are searchable. Charts, SmartArt, embedded
spreadsheets, images containing text, and unsupported objects need explicit
warnings; native PPTX parsing does not imply image OCR or complete SmartArt
understanding.

`python-pptx` is MIT licensed according to its
[official license](https://github.com/scanny/python-pptx/blob/master/LICENSE).

### Markdown: `markdown-it-py`

`markdown-it-py` provides a CommonMark token stream with block nesting and
source-line maps. That allows heading ancestry, lists, code blocks, tables when
enabled, and line-range citations to be preserved without flattening the source
to HTML. See its [token-stream documentation](https://markdown-it-py.readthedocs.io/en/latest/using.html)
and [project repository](https://github.com/executablebooks/markdown-it-py).

Choose and pin the supported Markdown profile, including whether raw HTML and
extensions such as tables and front matter are enabled. A profile change is a
parser-version change because it can alter block boundaries and evidence hashes.

### TXT

Plain text should be streamed by line, normalize newline conventions, preserve
line ranges, and reject binary-looking input. Decode UTF-8 first; any fallback
encoding policy must be bounded, recorded, and warning-producing. Do not erase
the original bytes or silently use the host locale.

## PDF alternatives and OCR

### PyMuPDF and PyMuPDF4LLM

PyMuPDF4LLM is a capable lightweight PDF path with Markdown, JSON, page chunks,
bounding boxes, table boxes, and OCR-page detection. It can run locally without
a GPU. See the official [PyMuPDF4LLM documentation](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/)
and [API reference](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/api.html).

It should not be the default unless licensing is consciously resolved.
PyMuPDF and PyMuPDF4LLM are offered under AGPL-3.0 for open-source use or a
commercial license for proprietary applications, as stated by the
[PyMuPDF project](https://github.com/pymupdf/PyMuPDF). This is a material
deployment decision, not a minor dependency detail.

### OCRmyPDF and Tesseract

OCRmyPDF creates a searchable PDF/PDF-A text layer and supports rotation,
deskewing, selective OCR modes, multiple CPU jobs, sidecar text, and OCR
timeouts. It is best treated as a retry/remediation stage for difficult PDFs,
not the canonical structured parser. It adds another complete PDF pass and
system dependencies. See the [OCRmyPDF project](https://github.com/ocrmypdf/OCRmyPDF),
[API](https://ocrmypdf.readthedocs.io/en/stable/apiref.html), and
[installation requirements](https://ocrmypdf.readthedocs.io/en/stable/installation.html).

Tesseract supports word confidence and bounding boxes, but its own documentation
notes that skew and image quality materially affect results and that table
recognition is weak without separate layout analysis. That supports using it as
an OCR engine underneath a layout-aware PDF parser rather than treating OCR text
as document structure. See the official [quality guidance](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html)
and [API examples](https://tesseract-ocr.github.io/tessdoc/APIExample.html).

OCRmyPDF is MPL-2.0; its project states that it can be integrated into closed or
commercial code while modifications to OCRmyPDF itself must be published.
Tesseract is Apache-2.0. OCRmyPDF also depends on external programs, and its
documentation specifically calls out Ghostscript and the need to consider
dependency licenses.

## Processing policy

The following behavior should be common to every adapter:

1. Verify file signature and container structure rather than trusting the
   filename extension alone.
2. Apply file-size, page/slide/sheet/row, decompression-ratio, time, memory, and
   subprocess limits before expensive work.
3. Parse in an isolated worker. Uploaded PDF and Office files are untrusted
   input; OCRmyPDF explicitly warns that it is not designed as a security
   boundary for malware-bearing PDFs.
4. Emit ordered canonical blocks and warnings. Never embed directly inside a
   parser adapter.
5. Run deterministic quality checks: non-empty usable content, valid ordering,
   location coverage, table sanity, and OCR confidence/coverage policy.
6. Fail a document with no usable content. Permit success with warnings only
   when usable content remains and release thresholds are met.
7. Persist parser/version/options/model checksums and aggregate metrics such as
   native-text pages, OCR pages, empty pages, table count, warning count, and
   elapsed time.

Automatic fallback between engines should be narrow and observable. Falling
back merely because an engine raised an exception can yield materially different
block boundaries and evidence hashes. Define the exact fallback trigger, record
both attempts, and do not activate a parse that fails the same quality contract.

## Evaluation before implementation approval

The supplied documents may be used as one test corpus, but they must not define
the parsers. Build a separate adversarial fixture set for every format,
including:

- native, scanned, mixed, rotated, multi-column, table-heavy, and malformed PDFs;
- DOCX headings, lists, nested/merged tables, headers/footers, tracked changes,
  text boxes, and embedded objects;
- XLSX merged cells, sparse sheets, incorrect dimensions, formulas with and
  without cached values, hidden sheets, and large workbooks;
- CSV delimiter, quoting, multiline-field, encoding, and malformed-row cases;
- PPTX grouped shapes, notes, tables, charts, SmartArt, and image-only slides;
- TXT and Markdown encoding, newline, heading, list, table, code, HTML, and
  extension cases.

Measure at least text recall, reading-order accuracy, table cell accuracy,
location/citation accuracy, warning correctness, false-success rate, wall time,
peak memory, and OCR page-selection accuracy. Quality gates should be defined
per format and per document class rather than as a single corpus average.

## Decision summary

- Adopt an application-owned canonical block and provenance contract.
- Use Docling as the primary PDF parser and evaluation baseline across formats.
- Use format-native adapters for Office, CSV, TXT, and Markdown to preserve
  exact source-native citation locations efficiently.
- Invoke English OCR selectively; use OCRmyPDF/Tesseract only as an observable
  remediation path for difficult PDFs.
- Do not adopt PyMuPDF/PyMuPDF4LLM without an explicit AGPL or commercial-license
  decision.
- Pin parser packages, model artifacts, options, and checksums; run ingestion in
  resource-limited isolated workers.
- Approve concrete parser choices only after the general adversarial benchmark
  meets the release quality thresholds required by `docs/specs.md`.
