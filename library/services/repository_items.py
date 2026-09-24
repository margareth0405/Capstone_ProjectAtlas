"""Persistence services for repository records and their stored files."""

import logging

from boto3.exceptions import S3UploadFailedError
from botocore.exceptions import BotoCoreError, ClientError
from django.db import transaction

logger = logging.getLogger(__name__)


class ResourceStorageError(RuntimeError):
    """Raised when a repository file cannot be written to configured storage."""


class RepositoryItemPersistenceService:
    """Keep repository database writes and private file storage coordinated."""

    file_fields = ("cover_image", "resource_abstract", "resource")
    storage_exceptions = (
        BotoCoreError,
        ClientError,
        S3UploadFailedError,
        OSError,
    )

    def save(self, form, *, prepare_instance):
        original_files = self._file_snapshots(form.instance)
        instance = prepare_instance(form.save(commit=False))
        try:
            with transaction.atomic():
                instance.save()
                form.save_m2m()
        except self.storage_exceptions as exc:
            self._remove_new_files(instance, original_files)
            raise ResourceStorageError(
                "The uploaded file could not be stored."
            ) from exc
        except Exception:
            # If the database write fails after a file was accepted by remote
            # storage, remove only the newly uploaded object and preserve the
            # file that belonged to an existing record.
            self._remove_new_files(instance, original_files)
            raise

        self._remove_replaced_files(instance, original_files)
        return instance

    def delete(self, instance):
        stored_files = self._file_snapshots(instance)
        with transaction.atomic():
            instance.delete()
        for storage, name in stored_files.values():
            self._safe_delete(storage, name)

    def _file_snapshots(self, instance):
        snapshots = {}
        for field_name in self.file_fields:
            field_file = getattr(instance, field_name, None)
            name = getattr(field_file, "name", "")
            if name:
                snapshots[field_name] = (field_file.storage, name)
        return snapshots

    def _remove_new_files(self, instance, original_files):
        for field_name in self.file_fields:
            field_file = getattr(instance, field_name, None)
            if not field_file or not getattr(field_file, "_committed", False):
                continue
            old_name = original_files.get(field_name, (None, ""))[1]
            if field_file.name and field_file.name != old_name:
                self._safe_delete(field_file.storage, field_file.name)

    def _remove_replaced_files(self, instance, original_files):
        for field_name, (storage, old_name) in original_files.items():
            current_name = getattr(getattr(instance, field_name), "name", "")
            if old_name and old_name != current_name:
                self._safe_delete(storage, old_name)

    @staticmethod
    def _safe_delete(storage, name):
        try:
            storage.delete(name)
        except Exception:
            # The database operation has already reached a safe state. Keep the
            # user request successful and leave an actionable server log for
            # orphan cleanup instead of returning a misleading failure page.
            logger.exception("Unable to remove repository storage object %s.", name)
