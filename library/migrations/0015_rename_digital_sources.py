from django.db import migrations


def rename_atlas_site(apps, schema_editor):
    Site = apps.get_model("sites", "Site")
    Site.objects.using(schema_editor.connection.alias).update_or_create(
        id=1,
        defaults={
            "domain": "atlas-repository.onrender.com",
            "name": "A.T.L.A.S. Digital Sources",
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0014_libraryitem_hard_copy_available"),
        ("sites", "0002_alter_domain_unique"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="libraryitem",
            options={
                "ordering": ("title", "author"),
                "verbose_name": "Digital Sources item",
                "verbose_name_plural": "Digital Sources items",
            },
        ),
        migrations.RunPython(rename_atlas_site, migrations.RunPython.noop),
    ]
