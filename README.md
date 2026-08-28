# ATLAS Django e-Library

ATLAS is now a conventional Django application. Django owns authentication,
sessions, permissions, validation, catalog data, favorites, announcements,
downloads, contact messages, and administration. The frontend remains regular
HTML, CSS, and presentation-only JavaScript.

## Technology

- Frontend: HTML rendered with Django templates, CSS, and JavaScript
- Backend: Python 3.12 and Django
- Database: PostgreSQL through the required `DATABASE_URL` setting
- Authentication: Django's built-in `User` and sessions with django-allauth
  for email identity, verification, and password recovery
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

Registration and login remain at `/register/` and `/login/` so ATLAS can
enforce role selection and privacy consent. django-allauth account recovery and
email-management endpoints are mounted under `/accounts/`. Email verification
is optional by default and uses Django's console email backend during local
development; set `ACCOUNT_EMAIL_VERIFICATION=mandatory` only after configuring
a production email backend.

Open <http://127.0.0.1:8000/>. PostgreSQL must be running and `DATABASE_URL`
must contain a valid PostgreSQL connection before running Django commands.

## Start from VS Code

The repository includes a one-command Windows startup script and matching VS
Code tasks. The first run creates `.venv` and installs `requirements.txt`;
later runs only reinstall dependencies when that file changes. It then activates
the environment, checks Django's configuration, and starts the development
server.

- Press Ctrl+Shift+P, choose **Tasks: Run Task**, then choose
  **ATLAS: Start Django**.
- Press Ctrl+Shift+B to run the same task as the default build task.
- Press F5 and choose **ATLAS: Start Django** to prepare the environment and
  start Django with the debugger.
- To run it without VS Code, use
  `powershell -ExecutionPolicy Bypass -File .\scripts\start_atlas.ps1`.

The `Bypass` setting applies only to the PowerShell process launched for the
task; it does not permanently change the computer's execution policy.

VS Code repository settings cannot safely replace the user-level Ctrl+Shift+P
keybinding. F5 and Ctrl+Shift+B start Django without a typed terminal command.

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
python manage.py check_database
python manage.py makemigrations --check --dry-run
python manage.py test
python manage.py collectstatic --noinput
```

## Project layout

```text
atlas/                          Django configuration and root URLs
library/
|-- models.py                  Domain entities and persistence rules
|-- forms.py                   Validation and form objects
|-- services/                  Reusable business/query services
|-- views/                     Class-based views grouped by feature
|   |-- authentication.py      Registration, login, and sessions
|   |-- catalog.py             Catalog, favorites, and downloads
|   |-- public.py              Dashboard, announcements, and contact
|   `-- staff.py               Staff portal and CRUD workflows
|-- migrations/                Database schema history
|-- management/commands/       Administrative CLI commands
`-- tests/                     Automated behavior tests
templates/library/             Server-rendered page templates
library/static/library/        Application CSS and JavaScript
legacy/prototype/              Archived pre-Django browser prototype
scripts/                       Local development automation
```

The application follows Django's OOP conventions: models and forms are classes,
HTTP behavior uses class-based views, common authorization/context behavior uses
mixins, and query/navigation logic lives in service objects. Dependencies flow
from views to services and models; models do not depend on the presentation
layer.

The original standalone `index.html`, `admin.html`, and browser-only
JavaScript are preserved under `legacy/prototype/` for reference. Django does
not load them. The active application is served from `templates/library/`,
`library/views/`, and `library/static/library/`.

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
