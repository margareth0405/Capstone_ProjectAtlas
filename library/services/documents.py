"""In-memory text extraction for supported AI Detection documents."""

from pathlib import Path


class DocumentExtractionError(ValueError):
    """Raised when text cannot be safely extracted from an uploaded document."""


class DocumentTextExtractor:
    """Extract bounded plain text from PDF and modern Word documents."""

    supported_extensions = frozenset({".pdf", ".docx"})
    minimum_characters = 100
    maximum_characters = 20000
    maximum_ai_pdf_pages = 75
    maximum_reading_pdf_pages = 250

    def extract(self, uploaded_file):
        extension = Path(uploaded_file.name).suffix.lower()
        if extension == ".pdf":
            text = self._extract_pdf(
                uploaded_file,
                character_limit=self.maximum_characters,
                page_limit=self.maximum_ai_pdf_pages,
            )
        elif extension == ".docx":
            text = self._extract_docx(
                uploaded_file,
                character_limit=self.maximum_characters,
            )
        else:
            raise DocumentExtractionError(
                "Upload a PDF or Word (.docx) document."
            )
        normalized = self._normalize(text)
        if len(normalized) < self.minimum_characters:
            raise DocumentExtractionError(
                "The document must contain at least 100 extractable characters. "
                "Scanned image-only PDFs require OCR before upload."
            )
        return normalized[: self.maximum_characters]

    def extract_for_reading(self, uploaded_file):
        """Extract readable text without exposing the original uploaded file."""

        extension = Path(uploaded_file.name).suffix.lower()
        if extension == ".pdf":
            text = self._extract_pdf(
                uploaded_file,
                character_limit=200000,
                page_limit=self.maximum_reading_pdf_pages,
            )
        elif extension == ".docx":
            text = self._extract_docx(uploaded_file, character_limit=200000)
        else:
            raise DocumentExtractionError(
                "This older Word format cannot be displayed safely. Ask the repository administrator to replace it with a .docx file."
            )
        normalized = self._normalize(text)
        if not normalized:
            raise DocumentExtractionError(
                "No readable text was found. Scanned image-only PDFs require OCR before they can be displayed."
            )
        return normalized[:200000]

    @staticmethod
    def _extract_pdf(uploaded_file, *, character_limit, page_limit):
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise DocumentExtractionError(
                "PDF support is unavailable. Install the project requirements."
            ) from exc

        try:
            uploaded_file.seek(0)
            reader = PdfReader(uploaded_file)
            if reader.is_encrypted:
                raise DocumentExtractionError(
                    "Password-protected PDF files are not supported."
                )
            parts = []
            character_count = 0
            for page_number, page in enumerate(reader.pages):
                if page_number >= page_limit or character_count >= character_limit:
                    break
                page_text = page.extract_text() or ""
                parts.append(page_text)
                character_count += len(page_text)
            return chr(10).join(parts)
        except DocumentExtractionError:
            raise
        except Exception as exc:
            raise DocumentExtractionError(
                "ATLAS could not read this PDF file."
            ) from exc

    @staticmethod
    def _extract_docx(uploaded_file, *, character_limit):
        try:
            from docx import Document
        except ImportError as exc:
            raise DocumentExtractionError(
                "Word support is unavailable. Install the project requirements."
            ) from exc

        try:
            uploaded_file.seek(0)
            document = Document(uploaded_file)
            parts = []
            character_count = 0

            def add_text(value):
                nonlocal character_count
                if not value or character_count >= character_limit:
                    return
                remaining = character_limit - character_count
                bounded = value[:remaining]
                parts.append(bounded)
                character_count += len(bounded)

            for paragraph in document.paragraphs:
                add_text(paragraph.text)
                if character_count >= character_limit:
                    break
            if character_count < character_limit:
                for table in document.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            for paragraph in cell.paragraphs:
                                add_text(paragraph.text)
                                if character_count >= character_limit:
                                    break
                            if character_count >= character_limit:
                                break
                        if character_count >= character_limit:
                            break
                    if character_count >= character_limit:
                        break
            return chr(10).join(parts)
        except Exception as exc:
            raise DocumentExtractionError(
                "ATLAS could not read this Word document."
            ) from exc

    @staticmethod
    def _normalize(text):
        return chr(10).join(
            line.strip() for line in text.splitlines() if line.strip()
        )
