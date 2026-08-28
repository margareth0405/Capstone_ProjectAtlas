from django.conf import settings
from django.db import migrations


def backfill_email_addresses(apps, schema_editor):
    app_label, model_name = settings.AUTH_USER_MODEL.split(".")
    user_model = apps.get_model(app_label, model_name)
    email_address_model = apps.get_model("account", "EmailAddress")

    users = user_model.objects.exclude(email="").exclude(email__isnull=True)
    for user in users.iterator():
        email = user.email.strip().lower()
        if not email:
            continue
        email_address, created = email_address_model.objects.get_or_create(
            user_id=user.pk,
            email=email,
            defaults={"primary": True, "verified": False},
        )
        if not created and not email_address_model.objects.filter(
            user_id=user.pk, primary=True
        ).exists():
            email_address.primary = True
            email_address.save(update_fields=["primary"])


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0009_emailaddress_unique_primary_email"),
        ("library", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(backfill_email_addresses, migrations.RunPython.noop),
    ]
