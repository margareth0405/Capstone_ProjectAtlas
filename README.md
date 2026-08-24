# ATLAS Django e-Library

ATLAS is now a conventional Django application. Django owns authentication,
sessions, permissions, validation, catalog data, favorites, announcements,
downloads, contact messages, and administration. The frontend remains regular
HTML, CSS, and presentation-only JavaScript.

## Technology

- Frontend: HTML rendered with Django templates, CSS, and JavaScript
- Backend: Python 3.12 and Django
- Database: PostgreSQL through the required `DATABASE_URL` setting
- Authentication: Django's built-in `User`, sessions, and password hashing
- Administration: Django Admin at the private path configured in `.env`
- Version control: Git with the GitHub `origin` repository
- Static file serving: WhiteNoise for deployed CSS and JavaScript assets

Node.js is not required.

## Local setup on Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env with your PostgreSQL username, password, and database name.
python manage.py migrate
python manage.py runserver
```

Open <http://127.0.0.1:8000/>. PostgreSQL must be running and `DATABASE_URL`
must contain a valid PostgreSQL connection before running Django commands.

The optional `python manage.py seed_atlas` command is idempotent and creates 33 catalog records, eight
announcements, and these development accounts:

| Role | Email | Password | Entry point |
| --- | --- | --- | --- |
| Student | `student@atlas.edu` | `password123` | `/login/` |
| Teacher | `teacher@deped.gov.ph` | `password123` | `/login/` |

The seed command never creates an administrator. Create administrators explicitly
with `python manage.py createsuperuser` and use a unique password.

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
```

## Administration

- Django Admin uses the private path configured by `DJANGO_ADMIN_PATH` in `.env`.
- The public frontend does not display or link to administrator sign-in.
- `/staff/` and Django Admin require an active Django staff or superuser account.
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
