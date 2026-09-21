from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0009_add_ai_analysis"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="age_consent_confirmed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="age_consent_version",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name="contactmessage",
            name="request_type",
            field=models.CharField(
                choices=[
                    ("support", "General support"),
                    ("privacy", "Privacy question"),
                    ("access_correction", "Access or correct my data"),
                    ("data_deletion", "Delete or block my data"),
                    ("email_preferences", "Email preferences"),
                ],
                db_index=True,
                default="support",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="contactmessage",
            name="privacy_consent_accepted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
