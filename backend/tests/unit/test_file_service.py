"""
Unit tests for ``app.services.file_service``.

Coverage target: 95%+

Tests cover:
    - FileParseError exception attributes
    - ResumeDocument defaults
    - Extension validation (is_allowed)
    - Full file validation (type, MIME, size)
    - PDF extraction (mocked pdfplumber)
    - DOCX extraction (mocked python-docx)
    - PII redaction
    - Section splitting
    - Upload save flow
"""

from __future__ import annotations

import os
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from app.services.file_service import (
    FileParseError,
    FileService,
    ResumeDocument,
    _redact,
    _split_sections,
)

pytestmark = pytest.mark.unit


# =====================================================================
# FileParseError
# =====================================================================

class TestFileParseError:
    """Tests for the custom exception."""

    def test_basic_message(self):
        err = FileParseError("bad file")
        assert str(err) == "bad file"
        assert err.filepath == ""
        assert err.cause is None

    def test_with_filepath_and_cause(self):
        cause = ValueError("inner")
        err = FileParseError("corrupt", filepath="/tmp/f.pdf", cause=cause)
        assert err.filepath == "/tmp/f.pdf"
        assert err.cause is cause

    def test_is_exception(self):
        assert issubclass(FileParseError, Exception)


# =====================================================================
# ResumeDocument
# =====================================================================

class TestResumeDocument:
    """Tests for the result dataclass."""

    def test_defaults(self):
        doc = ResumeDocument()
        assert doc.raw_text == ""
        assert doc.sections == {}
        assert doc.page_count == 0
        assert doc.file_type == ""

    def test_populated(self):
        doc = ResumeDocument(
            raw_text="hello", sections={"Header": "hi"},
            page_count=3, file_type="pdf",
        )
        assert doc.raw_text == "hello"
        assert doc.page_count == 3
        assert doc.file_type == "pdf"


# =====================================================================
# is_allowed
# =====================================================================

class TestIsAllowed:
    """Test extension validation."""

    @pytest.mark.parametrize("name,expected", [
        ("resume.pdf", True),
        ("doc.docx", True),
        ("RESUME.PDF", True),
        ("file.DOCx", True),
        ("image.png", False),
        ("noext", False),
        ("", False),
        (".pdf", True),
        ("resume.pdf.exe", False),
    ])
    def test_extensions(self, name, expected):
        assert FileService.is_allowed(name) is expected

    def test_custom_allowed_set(self):
        assert FileService.is_allowed("data.csv", allowed={"csv", "xlsx"}) is True
        assert FileService.is_allowed("data.pdf", allowed={"csv"}) is False


# =====================================================================
# validate
# =====================================================================

def _make_file_storage(
    filename: str,
    content: bytes = b"dummy",
    content_type: str = "application/pdf",
) -> MagicMock:
    """Create a mock Werkzeug FileStorage."""
    stream = BytesIO(content)
    fs = MagicMock()
    fs.filename = filename
    fs.content_type = content_type
    fs.stream = stream
    return fs


class TestValidate:
    """Test the full validate() flow."""

    def test_no_filename(self):
        fs = _make_file_storage(filename="")
        with pytest.raises(FileParseError, match="No filename"):
            FileService.validate(fs)

    def test_unsupported_extension(self):
        fs = _make_file_storage("photo.png", content_type="image/png")
        with pytest.raises(FileParseError, match="Unsupported file type"):
            FileService.validate(fs)

    def test_invalid_mime(self):
        fs = _make_file_storage(
            "resume.pdf",
            content_type="text/plain",
        )
        with patch("mimetypes.guess_type", return_value=("text/plain", None)):
            with pytest.raises(FileParseError, match="Invalid MIME"):
                FileService.validate(fs)

    def test_file_too_large(self):
        big = b"x" * (FileService.MAX_FILE_SIZE + 1)
        fs = _make_file_storage("resume.pdf", content=big)
        with pytest.raises(FileParseError, match="File too large"):
            FileService.validate(fs)

    def test_valid_pdf(self):
        content = b"%PDF-1.4 valid content"
        fs = _make_file_storage("resume.pdf", content=content)
        FileService.validate(fs)  # should not raise

    def test_valid_docx(self):
        fs = _make_file_storage(
            "resume.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        FileService.validate(fs)

    def test_stream_position_preserved(self):
        content = b"some content"
        fs = _make_file_storage("resume.pdf", content=content)
        fs.stream.seek(5)
        FileService.validate(fs)
        assert fs.stream.tell() == 5


# =====================================================================
# PDF extraction (mocked)
# =====================================================================

def _mock_pdfplumber(mock_pdf):
    """Context manager that patches pdfplumber at the import point inside
    ``FileService._read_pdf`` so it works even when pdfplumber is not
    installed in the test environment."""
    import sys
    fake_pdfplumber = MagicMock()
    fake_pdfplumber.open.return_value = mock_pdf
    return patch.dict(sys.modules, {"pdfplumber": fake_pdfplumber})


class TestPdfExtraction:
    """Test _read_pdf via mocked pdfplumber."""

    def test_successful_extraction(self, tmp_path):
        pdf_path = str(tmp_path / "resume.pdf")
        (tmp_path / "resume.pdf").write_bytes(b"%PDF")

        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "EDUCATION\nBS Computer Science"
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "EXPERIENCE\nSoftware Engineer"
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdf.__enter__ = lambda s: s
        mock_pdf.__exit__ = MagicMock(return_value=False)

        with _mock_pdfplumber(mock_pdf):
            doc = FileService.extract(pdf_path)

        assert "EDUCATION" in doc.raw_text
        assert "EXPERIENCE" in doc.raw_text
        assert doc.page_count == 2
        assert doc.file_type == "pdf"

    def test_empty_pdf(self, tmp_path):
        pdf_path = str(tmp_path / "empty.pdf")
        (tmp_path / "empty.pdf").write_bytes(b"%PDF")

        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = lambda s: s
        mock_pdf.__exit__ = MagicMock(return_value=False)

        with _mock_pdfplumber(mock_pdf):
            with pytest.raises(FileParseError, match="No text could be extracted"):
                FileService.extract(pdf_path)

    def test_corrupt_pdf(self, tmp_path):
        pdf_path = str(tmp_path / "corrupt.pdf")
        (tmp_path / "corrupt.pdf").write_bytes(b"not a pdf")

        import sys
        fake_pdfplumber = MagicMock()
        fake_pdfplumber.open.side_effect = Exception("corrupt")
        with patch.dict(sys.modules, {"pdfplumber": fake_pdfplumber}):
            with pytest.raises(FileParseError):
                FileService.extract(pdf_path)

    def test_file_not_found(self):
        with pytest.raises(FileParseError, match="File not found"):
            FileService.extract("/nonexistent/path.pdf")

    def test_unsupported_extension(self, tmp_path):
        txt_path = str(tmp_path / "file.txt")
        (tmp_path / "file.txt").write_text("hello")
        with pytest.raises(FileParseError, match="Unsupported file type"):
            FileService.extract(txt_path)


# =====================================================================
# DOCX extraction (mocked)
# =====================================================================

class TestDocxExtraction:
    """Test _read_docx via mocked python-docx."""

    def _make_para(self, text: str, style: str = "Normal") -> MagicMock:
        p = MagicMock()
        p.text = text
        p.style = MagicMock()
        p.style.name = style
        return p

    def test_successful_extraction(self, tmp_path):
        docx_path = str(tmp_path / "resume.docx")
        (tmp_path / "resume.docx").write_bytes(b"PK\x03\x04")

        mock_doc = MagicMock()
        mock_doc.paragraphs = [
            self._make_para("Education", "Heading 1"),
            self._make_para("BS Computer Science"),
            self._make_para("Skills", "Heading 2"),
            self._make_para("Python, JavaScript"),
            self._make_para("Item one", "List Bullet"),
        ]
        mock_doc.tables = []

        with patch("docx.Document", return_value=mock_doc):
            doc = FileService.extract(docx_path)

        assert "EDUCATION" in doc.raw_text  # headings uppercased
        assert "Python" in doc.raw_text
        assert doc.file_type == "docx"
        assert doc.page_count == 1

    def test_docx_with_tables(self, tmp_path):
        docx_path = str(tmp_path / "table.docx")
        (tmp_path / "table.docx").write_bytes(b"PK\x03\x04")

        mock_doc = MagicMock()
        mock_doc.paragraphs = [self._make_para("Skills\nPython")]

        cell1 = MagicMock()
        cell1.text = "Language"
        cell2 = MagicMock()
        cell2.text = "Level"
        row = MagicMock()
        row.cells = [cell1, cell2]
        table = MagicMock()
        table.rows = [row]
        mock_doc.tables = [table]

        with patch("docx.Document", return_value=mock_doc):
            doc = FileService.extract(docx_path)

        assert "Language | Level" in doc.raw_text

    def test_corrupt_docx(self, tmp_path):
        docx_path = str(tmp_path / "corrupt.docx")
        (tmp_path / "corrupt.docx").write_bytes(b"corrupt")

        with patch("docx.Document", side_effect=Exception("bad docx")):
            with pytest.raises(FileParseError, match="Corrupt or unreadable DOCX"):
                FileService.extract(docx_path)

    def test_empty_docx(self, tmp_path):
        docx_path = str(tmp_path / "empty.docx")
        (tmp_path / "empty.docx").write_bytes(b"PK\x03\x04")

        mock_doc = MagicMock()
        mock_doc.paragraphs = [self._make_para("")]
        mock_doc.tables = []

        with patch("docx.Document", return_value=mock_doc):
            with pytest.raises(FileParseError, match="No text could be extracted"):
                FileService.extract(docx_path)


# =====================================================================
# PII redaction
# =====================================================================

class TestPiiRedaction:
    """Test _redact helper for emails, phones, SSNs."""

    def test_email_redacted(self):
        assert "[EMAIL REDACTED]" in _redact("Contact: user@example.com")

    def test_ssn_redacted(self):
        assert "[SSN REDACTED]" in _redact("SSN: 123-45-6789")

    def test_phone_redacted(self):
        result = _redact("Call 555-123-4567")
        assert "[PHONE REDACTED]" in result

    def test_multiple_pii(self):
        text = "Email: a@b.com, SSN: 111-22-3333, Phone: 555-000-1234"
        result = _redact(text)
        assert "[EMAIL REDACTED]" in result
        assert "[SSN REDACTED]" in result
        assert "[PHONE REDACTED]" in result

    def test_no_pii(self):
        text = "This text has no personal information."
        assert _redact(text) == text

    def test_multiple_emails(self):
        text = "a@b.com and c@d.com"
        assert _redact(text).count("[EMAIL REDACTED]") == 2


# =====================================================================
# Section splitting
# =====================================================================

class TestSectionSplitting:
    """Test _split_sections helper."""

    def test_standard_sections(self):
        text = "John Smith\n\nEDUCATION\nBS CS\n\nEXPERIENCE\nDev at Acme"
        sections = _split_sections(text)
        assert "Education" in sections
        assert "Experience" in sections

    def test_no_sections(self):
        text = "Just some plain text without headings."
        sections = _split_sections(text)
        assert "header" in sections

    def test_skills_section(self):
        text = "Header\n\nSKILLS\nPython, Java\n\nEDUCATION\nBS"
        sections = _split_sections(text)
        assert "Skills" in sections
        assert "Python" in sections["Skills"]

    def test_preamble_captured(self):
        text = "Name And Title\n\nEDUCATION\nBS"
        sections = _split_sections(text)
        assert "Header" in sections
        assert "Name" in sections["Header"]

    def test_case_insensitive(self):
        text = "skills\nPython\neducation\nBS"
        sections = _split_sections(text)
        assert "Skills" in sections


# =====================================================================
# Save upload
# =====================================================================

class TestSaveUpload:
    """Test save_upload flow."""

    def test_save_success(self, tmp_path):
        content = b"%PDF valid content"
        fs = _make_file_storage("resume.pdf", content=content)
        fs.save = MagicMock(side_effect=lambda dest: open(dest, "wb").write(content))

        path = FileService.save_upload(fs, str(tmp_path))
        assert os.path.basename(path).endswith("_resume.pdf")
        assert str(tmp_path) in path
        fs.save.assert_called_once()

    def test_save_creates_directory(self, tmp_path):
        dest_dir = str(tmp_path / "new_subdir")
        content = b"%PDF"
        fs = _make_file_storage("resume.pdf", content=content)
        fs.save = MagicMock()

        FileService.save_upload(fs, dest_dir)
        assert os.path.isdir(dest_dir)

    def test_save_invalid_file_raises(self, tmp_path):
        fs = _make_file_storage("photo.png", content_type="image/png")
        with pytest.raises(FileParseError):
            FileService.save_upload(fs, str(tmp_path))

    def test_save_io_error(self, tmp_path):
        content = b"%PDF"
        fs = _make_file_storage("resume.pdf", content=content)
        fs.save = MagicMock(side_effect=IOError("disk full"))

        with pytest.raises(FileParseError, match="Failed to save"):
            FileService.save_upload(fs, str(tmp_path))
