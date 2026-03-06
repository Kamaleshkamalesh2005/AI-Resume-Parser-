"""
Unit tests for app.services.file_service
=========================================

Covers validation, extraction, PII redaction, and error handling using
mock file objects (no real PDF/DOCX binaries required).
"""

from __future__ import annotations

import io
import os
import textwrap
from unittest.mock import MagicMock, patch

import pytest

from app.services.file_service import (
    FileParseError,
    FileService,
    ResumeDocument,
    _redact,
    _split_sections,
)


# ── Helpers ──────────────────────────────────────────────────────────

def _make_file_storage(
    filename: str = "resume.pdf",
    content: bytes = b"%PDF-1.4 fake",
    content_type: str = "application/pdf",
) -> MagicMock:
    """Create a mock ``werkzeug.FileStorage``."""
    stream = io.BytesIO(content)
    fs = MagicMock()
    fs.filename = filename
    fs.content_type = content_type
    fs.stream = stream
    fs.save = MagicMock(side_effect=lambda dest: _write(dest, content))
    return fs


def _write(dest: str, data: bytes) -> None:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as f:
        f.write(data)


# =====================================================================
# ResumeDocument dataclass
# =====================================================================

class TestResumeDocument:
    def test_defaults(self):
        doc = ResumeDocument()
        assert doc.raw_text == ""
        assert doc.sections == {}
        assert doc.page_count == 0
        assert doc.file_type == ""

    def test_custom_values(self):
        doc = ResumeDocument(
            raw_text="hello",
            sections={"Header": "hi"},
            page_count=3,
            file_type="pdf",
        )
        assert doc.raw_text == "hello"
        assert doc.page_count == 3


# =====================================================================
# FileParseError
# =====================================================================

class TestFileParseError:
    def test_basic(self):
        err = FileParseError("bad file")
        assert str(err) == "bad file"
        assert err.filepath == ""
        assert err.cause is None

    def test_with_details(self):
        cause = ValueError("inner")
        err = FileParseError("corrupt", filepath="/tmp/x.pdf", cause=cause)
        assert err.filepath == "/tmp/x.pdf"
        assert err.cause is cause


# =====================================================================
# Validation
# =====================================================================

class TestValidation:
    def test_valid_pdf(self):
        fs = _make_file_storage("resume.pdf", b"x" * 100, "application/pdf")
        FileService.validate(fs)  # should not raise

    def test_valid_docx(self):
        fs = _make_file_storage(
            "resume.docx",
            b"x" * 100,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        FileService.validate(fs)

    def test_no_filename(self):
        fs = _make_file_storage("")
        with pytest.raises(FileParseError, match="No filename"):
            FileService.validate(fs)

    def test_unsupported_extension(self):
        fs = _make_file_storage("notes.txt", b"text", "text/plain")
        with pytest.raises(FileParseError, match="Unsupported file type"):
            FileService.validate(fs)

    def test_invalid_mime(self):
        # Use a filename whose guessed MIME is also wrong so neither
        # the browser-reported nor the guessed MIME passes the whitelist.
        fs = _make_file_storage("resume.pdf", b"x" * 10, "text/plain")
        fs.filename = "resume.pdf"
        with patch("app.services.file_service.mimetypes.guess_type", return_value=("text/plain", None)):
            with pytest.raises(FileParseError, match="Invalid MIME type"):
                FileService.validate(fs)

    def test_file_too_large(self):
        big = b"x" * (6 * 1024 * 1024)  # 6 MB
        fs = _make_file_storage("resume.pdf", big, "application/pdf")
        with pytest.raises(FileParseError, match="File too large"):
            FileService.validate(fs)

    def test_exactly_at_limit(self):
        data = b"x" * (5 * 1024 * 1024)  # exactly 5 MB
        fs = _make_file_storage("resume.pdf", data, "application/pdf")
        FileService.validate(fs)  # should pass


# =====================================================================
# is_allowed
# =====================================================================

class TestIsAllowed:
    def test_allowed_pdf(self):
        assert FileService.is_allowed("report.pdf") is True

    def test_allowed_docx(self):
        assert FileService.is_allowed("report.docx") is True

    def test_disallowed_txt(self):
        assert FileService.is_allowed("notes.txt") is False

    def test_no_extension(self):
        assert FileService.is_allowed("noext") is False

    def test_custom_allowed(self):
        assert FileService.is_allowed("data.csv", {"csv"}) is True


# =====================================================================
# save_upload
# =====================================================================

class TestSaveUpload:
    def test_save_success(self, tmp_path):
        fs = _make_file_storage("resume.pdf", b"data", "application/pdf")
        dest = FileService.save_upload(fs, str(tmp_path))
        assert os.path.isfile(dest)
        assert dest.endswith(".pdf")

    def test_save_creates_directory(self, tmp_path):
        target = str(tmp_path / "sub" / "dir")
        fs = _make_file_storage("r.pdf", b"data", "application/pdf")
        dest = FileService.save_upload(fs, target)
        assert os.path.isfile(dest)

    def test_save_rejects_invalid(self, tmp_path):
        fs = _make_file_storage("bad.exe", b"data", "application/octet-stream")
        with pytest.raises(FileParseError):
            FileService.save_upload(fs, str(tmp_path))


# =====================================================================
# extract – PDF
# =====================================================================

class TestExtractPDF:
    @patch("app.services.file_service.FileService._read_pdf")
    def test_extract_pdf(self, mock_read, tmp_path):
        # Create a dummy file so os.path.isfile passes
        pdf_path = str(tmp_path / "test.pdf")
        with open(pdf_path, "wb") as f:
            f.write(b"fake")

        mock_read.return_value = ("EXPERIENCE\nWorked at ACME", 2)
        doc = FileService.extract(pdf_path)

        assert isinstance(doc, ResumeDocument)
        assert doc.file_type == "pdf"
        assert doc.page_count == 2
        assert "ACME" in doc.raw_text
        assert "Experience" in doc.sections

    @patch("app.services.file_service.FileService._read_pdf")
    def test_extract_pdf_empty_text(self, mock_read, tmp_path):
        pdf_path = str(tmp_path / "empty.pdf")
        with open(pdf_path, "wb") as f:
            f.write(b"fake")

        mock_read.return_value = ("   ", 1)
        with pytest.raises(FileParseError, match="No text"):
            FileService.extract(pdf_path)

    @patch("app.services.file_service.FileService._read_pdf")
    def test_extract_pdf_corrupt(self, mock_read, tmp_path):
        pdf_path = str(tmp_path / "corrupt.pdf")
        with open(pdf_path, "wb") as f:
            f.write(b"fake")

        mock_read.side_effect = Exception("bad data")
        with pytest.raises(FileParseError, match="Failed to read PDF"):
            FileService.extract(pdf_path)

    def test_extract_file_not_found(self):
        with pytest.raises(FileParseError, match="File not found"):
            FileService.extract("/nonexistent/file.pdf")


# =====================================================================
# extract – DOCX
# =====================================================================

class TestExtractDOCX:
    @patch("app.services.file_service.FileService._read_docx")
    def test_extract_docx(self, mock_read, tmp_path):
        docx_path = str(tmp_path / "test.docx")
        with open(docx_path, "wb") as f:
            f.write(b"fake")

        mock_read.return_value = ("SKILLS\nPython, Flask", 1)
        doc = FileService.extract(docx_path)

        assert doc.file_type == "docx"
        assert doc.page_count == 1
        assert "Skills" in doc.sections

    def test_extract_unsupported(self, tmp_path):
        txt_path = str(tmp_path / "test.txt")
        with open(txt_path, "w") as f:
            f.write("hello")
        with pytest.raises(FileParseError, match="Unsupported file type"):
            FileService.extract(txt_path)


# =====================================================================
# PII redaction
# =====================================================================

class TestPIIRedaction:
    def test_redact_email(self):
        assert "[EMAIL REDACTED]" in _redact("contact me at john@example.com")

    def test_redact_phone(self):
        result = _redact("Call 555-123-4567 now")
        assert "[PHONE REDACTED]" in result

    def test_redact_ssn(self):
        assert "[SSN REDACTED]" in _redact("SSN: 123-45-6789")

    def test_no_pii(self):
        text = "Python developer with Flask experience"
        assert _redact(text) == text

    @patch("app.services.file_service._PII_REDACT", True)
    @patch("app.services.file_service.FileService._read_pdf")
    def test_extract_with_pii_redact(self, mock_read, tmp_path):
        pdf_path = str(tmp_path / "pii.pdf")
        with open(pdf_path, "wb") as f:
            f.write(b"fake")

        mock_read.return_value = (
            "SUMMARY\nJohn Doe john@example.com 555-123-4567",
            1,
        )
        doc = FileService.extract(pdf_path)
        assert "[EMAIL REDACTED]" in doc.raw_text
        assert "[PHONE REDACTED]" in doc.raw_text
        assert "john@example.com" not in doc.raw_text


# =====================================================================
# Section splitting
# =====================================================================

class TestSectionSplitting:
    def test_multiple_sections(self):
        text = textwrap.dedent("""\
            John Doe
            Software Engineer

            EDUCATION
            BS Computer Science

            EXPERIENCE
            Worked at ACME Corp

            SKILLS
            Python, Flask, SQL
        """)
        sections = _split_sections(text)
        assert "Header" in sections
        assert "Education" in sections
        assert "Experience" in sections
        assert "Skills" in sections
        assert "Python" in sections["Skills"]

    def test_no_headings(self):
        text = "Just some plain text with no sections"
        sections = _split_sections(text)
        assert "header" in sections
        assert sections["header"] == text.strip()

    def test_heading_variations(self):
        text = "TECHNICAL SKILLS\nPython\n\nWORK EXPERIENCE\n3 years"
        sections = _split_sections(text)
        assert "Technical Skills" in sections
        assert "Work Experience" in sections


# =====================================================================
# delete_file
# =====================================================================

class TestDeleteFile:
    def test_delete_existing(self, tmp_path):
        f = tmp_path / "deleteme.txt"
        f.write_text("bye")
        assert FileService.delete_file(str(f)) is True
        assert not f.exists()

    def test_delete_nonexistent(self):
        assert FileService.delete_file("/nonexistent/file.pdf") is False
