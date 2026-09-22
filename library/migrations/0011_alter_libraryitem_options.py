from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0010_privacy_requests_and_age_consent"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="libraryitem",
            options={
                "ordering": ("title", "author"),
                "verbose_name": "repository item",
                "verbose_name_plural": "repository items",
            },
        ),
    ]
