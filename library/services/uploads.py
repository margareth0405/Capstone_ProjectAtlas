"""Reusable validation policies for untrusted document uploads."""

from pathlib import Path
from zipfile import BadZipFile, ZipFile


class DocumentUploadValidationError(ValueError):
    """Raised when a file's contents do not match its advertised format."""


class DocumentUploadPolicy:
    """Validate PDF and DOCX signatures without persisting the uploaded file."""

    supported_extensions = {".pdf", ".docx"}
    required_docx_members = {"[Content_Types].xml", "word/document.xml"}

    def validate(self, uploaded_file):
        extension = Path(uploaded_file.name).suffix.lower()
        if extension not in self.supported_extensions:
            raise DocumentUploadValidationError(
                "Upload a genuine PDF or Word (.docx) document."
            )

        original_position = uploaded_file.tell()
        try:
            uploaded_file.seek(0)
            if extension == ".pdf":
                if uploaded_file.read(5) != b"%PDF-":
                    raise DocumentUploadValidationError(
                        "The uploaded file is not a valid PDF document."
                    )
            else:
                try:
                    with ZipFile(uploaded_file) as archive:
                        members = set(archive.namelist())
                except (BadZipFile, OSError, ValueError) as exc:
                    raise DocumentUploadValidationError(
                        "The uploaded file is not a valid Word (.docx) document."
                    ) from exc
                if not self.required_docx_members.issubset(members):
                    raise DocumentUploadValidationError(
                        "The uploaded file is not a valid Word (.docx) document."
                    )
        finally:
            uploaded_file.seek(original_position)
        return uploaded_file
