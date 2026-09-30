"""Reusable validation policies for untrusted document uploads."""

from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile


class DocumentUploadValidationError(ValueError):
    """Raised when a file's contents do not match its advertised format."""


class DocumentUploadPolicy:
    """Validate PDF and DOCX signatures without persisting the uploaded file."""

    supported_extensions = frozenset({".pdf", ".docx"})
    required_docx_members = frozenset({"[Content_Types].xml", "word/document.xml"})
    maximum_docx_members = 2048
    maximum_docx_member_size = 50 * 1024 * 1024
    maximum_docx_uncompressed_size = 100 * 1024 * 1024
    maximum_compression_ratio = 200

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
                        members = self._validated_docx_members(archive)
                except DocumentUploadValidationError:
                    raise
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

    def _validated_docx_members(self, archive):
        entries = archive.infolist()
        if len(entries) > self.maximum_docx_members:
            raise DocumentUploadValidationError(
                "The Word document contains too many internal files."
            )

        total_size = 0
        members = set()
        for entry in entries:
            member_path = PurePosixPath(entry.filename)
            if (
                member_path.is_absolute()
                or ".." in member_path.parts
                or entry.flag_bits & 0x1
            ):
                raise DocumentUploadValidationError(
                    "The Word document contains unsafe archive entries."
                )

            total_size += entry.file_size
            if (
                entry.file_size > self.maximum_docx_member_size
                or total_size > self.maximum_docx_uncompressed_size
            ):
                raise DocumentUploadValidationError(
                    "The Word document expands beyond the safe processing limit."
                )

            if entry.file_size >= 1024 * 1024:
                compression_ratio = entry.file_size / max(entry.compress_size, 1)
                if compression_ratio > self.maximum_compression_ratio:
                    raise DocumentUploadValidationError(
                        "The Word document contains unsafe compressed content."
                    )
            members.add(entry.filename)
        return members
