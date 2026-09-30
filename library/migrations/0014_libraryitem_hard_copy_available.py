from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0013_rename_ai_analysis_validation_result"),
    ]

    operations = [
        migrations.AddField(
            model_name="libraryitem",
            name="hard_copy_available",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Indicates whether readers can request a physical copy from the "
                    "library."
                ),
            ),
        ),
    ]
