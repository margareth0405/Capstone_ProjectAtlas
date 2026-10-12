from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0018_preserve_resource_change_history"),
    ]

    operations = [
        migrations.AddField(
            model_name="libraryitem",
            name="submission_notes",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="resourcechangerequest",
            name="changed_fields",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="resourcechangerequest",
            name="request_notes",
            field=models.TextField(blank=True),
        ),
    ]
