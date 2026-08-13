import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ContactMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150)),
                ('email', models.EmailField(max_length=254)),
                ('subject', models.CharField(max_length=255)),
                ('message', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('is_resolved', models.BooleanField(db_index=True, default=False)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='contact_messages', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-created_at',),
            },
        ),
        migrations.CreateModel(
            name='LibraryItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('collection', models.CharField(choices=[('book', 'Book'), ('journal', 'Journal'), ('research', 'Research'), ('activity_sheets', 'Activity Sheets'), ('curriculum_guide', 'Curriculum Guide')], db_index=True, max_length=32)),
                ('call_number', models.CharField(max_length=80, unique=True)),
                ('title', models.CharField(db_index=True, max_length=255)),
                ('author', models.CharField(db_index=True, max_length=255)),
                ('details', models.TextField(blank=True)),
                ('file_type', models.CharField(default='PDF', max_length=20)),
                ('file_size', models.CharField(blank=True, max_length=32)),
                ('pages', models.PositiveIntegerField(default=0)),
                ('resource', models.FileField(blank=True, upload_to='library/resources/%Y/%m/')),
                ('external_url', models.URLField(blank=True)),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_library_items', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('title', 'author'),
            },
        ),
        migrations.CreateModel(
            name='Favorite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorite_links', to=settings.AUTH_USER_MODEL)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorite_links', to='library.libraryitem')),
            ],
            options={
                'ordering': ('-created_at',),
            },
        ),
        migrations.CreateModel(
            name='DownloadEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('downloaded_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.CharField(blank=True, max_length=500)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='download_events', to=settings.AUTH_USER_MODEL)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='download_events', to='library.libraryitem')),
            ],
            options={
                'ordering': ('-downloaded_at',),
            },
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('student', 'Student'), ('teacher', 'Teacher')], default='student', max_length=20)),
                ('privacy_consent_accepted_at', models.DateTimeField(blank=True, null=True)),
                ('privacy_consent_version', models.CharField(blank=True, max_length=32)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('user__email',),
            },
        ),
        migrations.CreateModel(
            name='Announcement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('body', models.TextField()),
                ('category', models.CharField(choices=[('general', 'General'), ('event', 'Event'), ('maintenance', 'Maintenance'), ('resource', 'Resource'), ('urgent', 'Urgent')], db_index=True, default='general', max_length=20)),
                ('is_featured', models.BooleanField(default=False)),
                ('is_published', models.BooleanField(db_index=True, default=True)),
                ('published_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='announcements_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-published_at', '-created_at'),
                'constraints': [models.CheckConstraint(condition=models.Q(('is_published', False), ('published_at__isnull', False), _connector='OR'), name='published_announcement_has_date')],
            },
        ),
        migrations.AddIndex(
            model_name='libraryitem',
            index=models.Index(fields=['collection', 'title'], name='library_col_title_idx'),
        ),
        migrations.AddConstraint(
            model_name='favorite',
            constraint=models.UniqueConstraint(fields=('user', 'item'), name='unique_user_library_favorite'),
        ),
    ]
