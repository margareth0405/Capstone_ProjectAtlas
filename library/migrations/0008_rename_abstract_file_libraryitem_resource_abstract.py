from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0007_libraryitem_abstract_file_libraryitem_cover_image"),
    ]

    operations = [
        migrations.RenameField(
            model_name="libraryitem",
            old_name="abstract_file",
            new_name="resource_abstract",
        ),
        migrations.AlterField(
            model_name="libraryitem",
            name="resource_abstract",
            field=models.FileField(upload_to="library/abstracts/%Y/%m/"),
        ),
    ]
