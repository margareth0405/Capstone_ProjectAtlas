# ATLAS Django e-Library

ATLAS is now a conventional Django application. Django owns authentication,
sessions, permissions, validation, catalog data, favorites, announcements,
downloads, contact messages, and administration. The frontend remains regular
HTML, CSS, and presentation-only JavaScript.

## Technology

- Python 3.12 and Django
- Django's built-in `User`, session authentication, password hashing, and Admin
- PostgreSQL through `DATABASE_URL` (SQLite is the local fallback)
- Server-rendered Django templates with CSRF-protected forms
- Existing ATLAS CSS plus a small Django integration stylesheet
- Plain JavaScript only for menus, password visibility, confirmations, copy,
  share, messages, and scroll-to-top behavior

Node.js is not required.

## Local setup on Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py seed_atlas
python manage.py runserver
```

Open <http://127.0.0.1:8000/>. The copied environment file leaves
`DATABASE_URL` commented, so local development uses SQLite.

The optional seed command is idempotent and creates 33 catalog records, eight
announcements, and these development accounts:

| Role | Email | Password | Entry point |
| --- | --- | --- | --- |
| Student | `student@atlas.edu` | `password123` | `/login/` |
| Teacher | `teacher@atlas.edu` | `password123` | `/login/` |
| Administrator | `admin@atlas.edu` | `password123` | `/django-admin/` |

These are demo credentials only. Change or remove them before deployment. For
example, run `python manage.py changepassword admin@atlas.edu`.

## PostgreSQL setup

Create a PostgreSQL database and account using your preferred administration
tool, then edit `.env` and uncomment/set:

```dotenv
DATABASE_URL=postgresql://atlas_user:strong-password@localhost:5432/atlas
DB_SSL_REQUIRE=False
```

For a hosted PostgreSQL service, use its full connection URL and set
`DB_SSL_REQUIRE=True` when the provider requires TLS. Then run:

```powershell
python manage.py migrate
python manage.py seed_atlas
```

Django uses the same models and migrations with SQLite and PostgreSQL, so no
application code needs to change when switching databases.

## Administration

- `/django-admin/` is Django's built-in administrative interface.
- `/staff/` is the ATLAS-branded staff overview for authorized Django staff.
- Only `is_staff` or superuser accounts can enter staff routes.
- The branded staff account form can create students and teachers only. Create
  administrators with `python manage.py createsuperuser` or Django Admin.
- Passwords are never stored in browser storage or in plain text.

## Important commands

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python manage.py collectstatic --noinput
```

## Project layout

```text
atlas/                    Django project settings and root URLs
library/                  Models, forms, views, Admin, migrations, tests
templates/library/        Server-rendered HTML templates
static/library/           Django-specific CSS and presentation JavaScript
css/                      Existing ATLAS theme loaded through Django staticfiles
media/                    Uploaded library resources (created at runtime)
```

The original root `index.html`, `admin.html`, and `js/` prototype files are
preserved for reference and to protect pre-existing local edits, but Django does
not load them. The active application is served from `templates/library/` and
`library/views.py`.

## Production checklist

Set a unique secret and production host values in the deployment environment:

```dotenv
DJANGO_SECRET_KEY=use-a-long-random-production-secret
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=library.example.edu
DJANGO_CSRF_TRUSTED_ORIGINS=https://library.example.edu
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
```

Only enable HSTS after HTTPS is working for the domain. Also configure durable
media storage for uploaded resources, run migrations and `collectstatic`, and
replace all demo passwords before exposing the site publicly.
