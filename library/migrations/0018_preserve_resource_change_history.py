from django.db import migrations, models
import django.db.models.deletion


def snapshot_resource_labels(apps, schema_editor):
    ResourceChangeRequest = apps.get_model("library", "ResourceChangeRequest")
    for change in ResourceChangeRequest.objects.select_related("item").iterator():
        if change.item_id:
            change.item_title = change.item.title
            change.item_call_number = change.item.call_number
            change.save(update_fields=("item_title", "item_call_number"))


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0017_resourcechangerequest"),
    ]

    operations = [
        migrations.AddField(
            model_name="resourcechangerequest",
            name="item_call_number",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="resourcechangerequest",
            name="item_title",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="resourcechangerequest",
            name="item",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="change_requests",
                to="library.libraryitem",
            ),
        ),
        migrations.RunPython(snapshot_resource_labels, migrations.RunPython.noop),
    ]
