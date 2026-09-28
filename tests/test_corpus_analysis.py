from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
import zipfile

from contextlib import suppress
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "analyze_corpus.py"
SPEC = importlib.util.spec_from_file_location("analyze_corpus", MODULE_PATH)
analyze_corpus = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = analyze_corpus
SPEC.loader.exec_module(analyze_corpus)


class CorpusAnalysisTests(unittest.TestCase):
    def test_discovery_is_sorted_and_excludes_hidden_certbot_and_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "b.pdf").write_bytes(b"%PDF-b")
            (root / "a.pdf").write_bytes(b"%PDF-a")
            (root / ".hidden.pdf").write_bytes(b"%PDF-hidden")
            (root / "certbot").mkdir()
            (root / "certbot" / "ignored.pdf").write_bytes(b"%PDF-ignore")
            (root / ".hidden").mkdir()
            (root / ".hidden" / "ignored.pdf").write_bytes(b"%PDF-ignore")
            with suppress(OSError):
                (root / "linked.pdf").symlink_to(root / "a.pdf")

            paths = analyze_corpus.discover_files(root)

            self.assertEqual([path.name for path in paths], ["a.pdf", "b.pdf"])

    def test_max_files_selects_supported_files_only(self):
        paths = [Path("a.bin"), Path("b.pdf"), Path("c.xlsx"), Path("d.docx")]

        selected = analyze_corpus.select_files(paths, max_files=2)

        self.assertEqual(selected, [Path("b.pdf"), Path("c.xlsx")])

    def test_pdf_signature_and_invalid_office_container_are_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pdf = root / "broken.pdf"
            pdf.write_bytes(b"not a PDF")
            workbook = root / "broken.xlsx"
            workbook.write_bytes(b"not a ZIP")

            pdf_record = analyze_corpus.inspect_file(pdf, root)
            workbook_record = analyze_corpus.inspect_file(workbook, root)

            self.assertEqual(pdf_record.status, "failure")
            self.assertIn("signature", pdf_record.errors[0])
            self.assertEqual(workbook_record.status, "failure")
            self.assertIn("ZIP", workbook_record.errors[0])

    def test_valid_office_container_and_unsafe_path_detection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workbook = root / "valid.xlsx"
            with zipfile.ZipFile(workbook, "w") as archive:
                archive.writestr("xl/workbook.xml", "<workbook />")

            record = analyze_corpus.inspect_file(workbook, root)

            self.assertEqual(record.integrity, "valid")
            self.assertTrue(analyze_corpus.is_unsafe_archive_path("../escape.xml"))
            self.assertFalse(analyze_corpus.is_unsafe_archive_path("xl/workbook.xml"))

    def test_xlsx_formula_count_includes_missing_cached_values(self):
        with tempfile.TemporaryDirectory() as directory:
            workbook = Path(directory) / "formulas.xlsx"
            worksheet = """\
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData><row r="1">
    <c r="A1"><f>SUM(B1:B2)</f><v>3</v></c>
    <c r="A2"><f>SUM(B1:B2)</f></c>
  </row></sheetData>
</worksheet>
"""
            with zipfile.ZipFile(workbook, "w") as archive:
                archive.writestr("xl/workbook.xml", "<workbook />")
                archive.writestr("xl/worksheets/sheet1.xml", worksheet)

            counts = analyze_corpus.inspect_xlsx_formulas(workbook)

            self.assertEqual(counts, (2, 1))

    def test_duplicate_and_casefolded_filename_groups(self):
        first = self.make_record("one/Policy.PDF", "same")
        second = self.make_record("two/policy.pdf", "same")
        third = self.make_record("three/other.pdf", "different")

        duplicates = analyze_corpus.duplicate_groups([first, second, third])
        collisions = analyze_corpus.filename_collisions([first, second, third])

        self.assertEqual(duplicates, [[first, second]])
        self.assertEqual(collisions, [[first, second]])

    def test_page_classification(self):
        self.assertEqual(analyze_corpus.classify_page(3, 0), "native-only")
        self.assertEqual(
            analyze_corpus.classify_page(0, 3), "ocr-only scan candidate"
        )
        self.assertEqual(analyze_corpus.classify_page(3, 2), "mixed")
        self.assertEqual(analyze_corpus.classify_page(0, 0), "empty")

    def test_document_failure_is_captured_without_raising(self):
        class FailingConverter:
            @staticmethod
            def convert(*_args, **_kwargs):
                raise RuntimeError("parser failed")

        record = self.make_record("broken.pdf", "digest")

        analyze_corpus.analyze_record(record, FailingConverter())

        self.assertEqual(record.status, "failure")
        self.assertEqual(record.errors, ["RuntimeError: parser failed"])

    def test_ocr_page_metrics_accept_docling_page_list(self):
        class Page:
            page_no = 7
            assembled = None

        self.assertEqual(analyze_corpus.ocr_cells_by_page([Page()]), {7: (0, 0)})

    def test_word_count_and_markdown_escaping(self):
        self.assertEqual(analyze_corpus.word_count("one two\nthree"), 3)
        self.assertEqual(
            analyze_corpus.escape_markdown("column | value\nnext"),
            "column \\| value<br>next",
        )

    @staticmethod
    def make_record(relative_path: str, digest: str):
        return analyze_corpus.FileRecord(
            path=Path(relative_path),
            relative_path=relative_path,
            extension=".pdf",
            sha256=digest,
        )


if __name__ == "__main__":
    unittest.main()
