"""Automatic screening and visibility rules for repository submissions."""

import logging

from botocore.exceptions import BotoCoreError, ClientError
from django.db import DatabaseError
from django.db.models import Q

from library.models import AIAnalysis, LibraryItem, Profile

from .ai_detection import AIDetectionError, AIDetectionService
from .documents import DocumentExtractionError, DocumentTextExtractor

logger = logging.getLogger(__name__)


def is_teacher(user):
    """Return whether an authenticated account has the reader-facing teacher role."""

    profile = getattr(user, "profile", None) if user.is_authenticated else None
    return profile is not None and profile.role == Profile.Role.TEACHER


def visible_library_items(user):
    """Return only resources the current role is allowed to discover or read."""

    items = LibraryItem.objects.all()
    if user.is_authenticated and user.is_staff:
        return items
    if is_teacher(user):
        return items.filter(
            Q(review_status=LibraryItem.ReviewStatus.APPROVED)
            | Q(created_by=user)
        )
    return items.filter(review_status=LibraryItem.ReviewStatus.APPROVED)


class ResourceReviewAnalysisService:
    """Screen a stored resource abstract without retaining its extracted text."""

    extractor_class = DocumentTextExtractor
    analyzer_class = AIDetectionService

    def analyze(self, item, *, reviewer):
        document = item.resource_abstract
        try:
            document.open("rb")
            text = self.extractor_class().extract(document)
            result = self.analyzer_class().analyze(text)
        except (
            BotoCoreError,
            ClientError,
            DocumentExtractionError,
            AIDetectionError,
            OSError,
            ValueError,
        ) as error:
            logger.warning(
                "Automatic review failed for repository item %s: %s",
                item.pk,
                error,
            )
            item.ai_review_status = LibraryItem.AIReviewStatus.FAILED
            item.ai_review_summary = {"error": str(error)}
            item.save(update_fields=("ai_review_status", "ai_review_summary", "updated_at"))
            return False
        finally:
            try:
                document.close()
            except OSError:
                logger.warning(
                    "Unable to close the review document for item %s.",
                    item.pk,
                    exc_info=True,
                )

        summary = {
            "label": result.get("label", ""),
            "tone": result.get("tone", ""),
            "ai_probability": float(result.get("ai_probability", 0)),
            "human_probability": float(result.get("human_probability", 0)),
            "confidence": float(result.get("confidence", 0)),
            "chunks_analyzed": int(result.get("chunks_analyzed", 0)),
            "detector_name": result.get("detector_name", ""),
            "model_name": result.get("model_name", ""),
            "model_version": result.get("model_version", ""),
            "fallback_used": bool(result.get("fallback_used", False)),
        }
        item.ai_review_status = LibraryItem.AIReviewStatus.COMPLETED
        item.ai_review_summary = summary
        item.save(update_fields=("ai_review_status", "ai_review_summary", "updated_at"))
        try:
            AIAnalysis.record(
                reviewer=reviewer,
                source_name=document.name.rsplit("/", 1)[-1],
                result=result,
            )
        except DatabaseError:
            logger.exception(
                "Unable to save AI analysis history for repository item %s.",
                item.pk,
            )
        return True
