"""Object-oriented audit logging for staff-visible ATLAS activity."""

from library.models import ActivityLog


class ActivityRecorder:
    """Create concise, durable activity records from application workflows."""

    model = ActivityLog

    @classmethod
    def record(cls, *, actor, action, object_type, object_id="", description):
        return cls.model.objects.create(
            actor=actor if getattr(actor, "is_authenticated", False) else None,
            action=action,
            object_type=object_type,
            object_id=str(object_id or ""),
            description=description[:500],
        )
