# ATLAS Django e-Library

ATLAS is a role-aware digital library for guests, students, teachers, and
administrators. Django owns authentication, permissions, validation, catalog
records, downloads, announcements, contact messages, staff activity history,
website-usage analytics, and the administrator AI Detection service.

The active interface is server-rendered HTML and CSS with presentation-only
JavaScript. Node.js is not required.

## Main features

### Guests, students, and teachers

- Browse, search, filter, and sort the library catalog.
- View published announcements.
- Submit support messages to atlasttshs@gmail.com.
- Register and sign in as a student or teacher.
- Download resources and save favorites when authenticated.

### Administrators

- Create, edit, and delete library resources.
- Create, edit, publish, and delete announcements.
- Create student and teacher accounts.
- Search accounts by name or email.
- Filter accounts by student, teacher, or administrator.
- Sort accounts from newest to oldest or oldest to newest.
- Delete reader accounts while protecting the active administrator and
  superusers.
- Review and delete download records.
- Review a dated audit history of resource, account, announcement, and download
  actions.
- Review website usage by role, date, session history, and approximate active
  time.
- Analyze pasted writing with the administrator-only AI Detection service.

AI Detection reports explainable writing-pattern indicators such as vocabulary
diversity, sentence-length variation, and repeated phrases. It cannot prove who
or what authored a document and must not be used as the sole basis for an
academic decision.

## Technology

- Python 3.12
- Django
- PostgreSQL through DATABASE_URL
- django-allauth for email identity, verification, and password recovery
- WhiteNoise for deployed static assets
- HTML, CSS, Bootstrap-compatible markup, and presentation JavaScript

## Local setup on Windows PowerShell

~~~powershell
python -m venv .venv
..venvScriptsActivate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env with your PostgreSQL and administrator-path settings.
python manage.py migrate
python manage.py runserver
~~~

Open http://127.0.0.1:8000/. PostgreSQL must be running and DATABASE_URL must
point to an existing database before running Django commands.

Registration and role-aware login are available at /register/ and /login/.
django-allauth account management is mounted under /accounts/.

## Start from VS Code

The repository contains a Windows startup script and matching VS Code tasks.

- Press Ctrl+Shift+P, choose Tasks: Run Task, and select
  ATLAS: Start Django.
- Press Ctrl+Shift+B to use the default build task.
- Press F5 and select ATLAS: Start Django to run with the debugger.
- Without VS Code, run:

  ~~~powershell
  powershell -ExecutionPolicy Bypass -File .scriptsstart_atlas.ps1
  ~~~

The first run creates .venv and installs dependencies. Later runs reinstall
only when requirements.txt changes.

## Environment configuration

Copy .env.example to .env. Never commit the real .env file or any database
password, Django secret, or Gmail App Password.

Minimum development settings:

~~~dotenv
DJANGO_SECRET_KEY=replace-with-a-long-random-secret
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_ADMIN_PATH=replace-with-a-private-admin-path
DATABASE_URL=postgresql://atlas_user:strong-password@localhost:5432/atlas
DB_SSL_REQUIRE=False
~~~

For a hosted PostgreSQL service, use the provider's complete connection URL and
set DB_SSL_REQUIRE=True when TLS is required.

## Contact email delivery

Contact submissions are addressed to atlasttshs@gmail.com. Each message
contains the visitor's name, submitted email, authenticated account email when
available, subject, and message. Reply-To is set to the visitor's submitted
email.

The console backend is safe for local development but prints messages instead
of delivering them:

~~~dotenv
DJANGO_EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
SUPPORT_EMAIL=atlasttshs@gmail.com
SUPPORT_HOURS=Monday–Friday, 8:00 AM–5:00 PM
~~~

For real Gmail delivery, create a Google App Password and use:

~~~dotenv
DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DEFAULT_FROM_EMAIL=ATLAS <atlasttshs@gmail.com>
SUPPORT_EMAIL=atlasttshs@gmail.com
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=atlasttshs@gmail.com
EMAIL_HOST_PASSWORD=your-google-app-password
~~~

Do not use the normal Gmail password. If delivery fails, ATLAS keeps the form
visible, shows an error, and does not record the message as successfully sent.

## Administrator setup

The administrator login is intentionally absent from public navigation.

1. Set a private DJANGO_ADMIN_PATH value in .env.
2. Apply migrations and create a superuser:

   ~~~powershell
   python manage.py migrate
   python manage.py createsuperuser
   ~~~

3. Start Django and open:

   ~~~text
   http://127.0.0.1:8000/<DJANGO_ADMIN_PATH>/
   ~~~

4. After signing in, open /staff/ for the branded Administrator Portal.

The staff account form creates students and teachers only. Create additional
administrators through createsuperuser or Django Admin.

## Optional development data

The idempotent command below creates catalog records, announcements, and reader
accounts:

~~~powershell
python manage.py seed_atlas
~~~

| Role | Email | Password | Entry point |
| --- | --- | --- | --- |
| Student | student@atlas.edu | password123 | /login/ |
| Teacher | teacher@deped.gov.ph | password123 | /login/ |

The seed command never creates an administrator. Replace development passwords
before sharing an environment.

## Object-oriented architecture

ATLAS follows Django's OOP conventions:

- Models represent persisted domain entities and validation rules.
- Forms encapsulate input validation and safe persistence.
- Class-based views coordinate HTTP requests and responses.
- Mixins provide shared page context and staff authorization.
- Service classes own reusable business logic and queries.
- Middleware delegates session tracking to a service object.
- Views use replaceable service-class attributes for testability.

Dependencies flow from views and middleware to services and models. Models do
not import templates or views.

~~~text
atlas/
|-- settings.py                         Environment-based Django configuration
+-- urls.py                             Root routing and private Django Admin

library/
|-- models.py                           Domain entities and persistence rules
|-- forms.py                            Authentication, content, contact, and AI forms
|-- middleware.py                       Thin request/response integration
|-- services/
|   |-- activity.py                     ActivityRecorder
|   |-- ai_detection.py                 WritingPatternAnalyzer
|   |-- catalog.py                      CatalogQueryService
|   |-- contact.py                      ContactEmailService
|   |-- context.py                      PageContextBuilder
|   |-- navigation.py                   SafeRedirectService
|   |-- staff_portal.py                 StaffUserDirectory, UsageAnalytics,
|   |                                    and StaffPortalContextService
|   +-- usage.py                        WebsiteUsageTracker
|-- views/
|   |-- authentication.py               Registration, login, guest, and logout
|   |-- catalog.py                      Catalog, favorites, and downloads
|   |-- public.py                       Dashboard, announcements, and contact
|   |-- mixins.py                       Context and staff permission mixins
|   |-- staff.py                        Stable administrator-view import facade
|   |-- staff_dashboard.py              Administrator homepage
|   |-- staff_crud.py                   Resource and announcement CRUD
|   |-- staff_accounts.py               Accounts and download records
|   +-- staff_ai.py                     AI Detection workflow
|-- migrations/                         Database schema history
|-- management/commands/                Administrative CLI commands
+-- tests/                              Automated behavior and security tests

templates/library/
|-- admin/                              Administrator forms and AI Detection
|-- includes/                           Shared template fragments
+-- *.html                              Public and role-aware pages

library/static/library/
|-- css/                                Shared and role-specific styles
+-- js/app.js                           Presentation-only browser behavior
~~~

library.views.staff re-exports the administrator view classes. This facade keeps
route imports stable while each implementation lives in its
responsibility-specific file.

## Usage tracking and audit history

WebsiteUsageMiddleware delegates to WebsiteUsageTracker. A visit is tracked for
authenticated users and guest-mode sessions. Requests separated by more than
15 minutes start a new visit. Reported duration is approximate active browsing
time, not surveillance of activity outside ATLAS.

ActivityRecorder stores create, update, delete, and download events displayed
in the administrator history panel. Records created before the audit feature
was installed are not reconstructed retroactively.

## Important commands

~~~powershell
python manage.py check
python manage.py check_database
python manage.py makemigrations --check --dry-run
python manage.py test
python manage.py collectstatic --noinput
~~~

Focused administrator tests:

~~~powershell
python manage.py test library.tests.test_staff_views library.tests.test_staff_features
~~~

## Production checklist

~~~dotenv
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=library.example.edu
DJANGO_CSRF_TRUSTED_ORIGINS=https://library.example.edu
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
DB_SSL_REQUIRE=True
~~~

Also:

- Use a unique production DJANGO_SECRET_KEY.
- Configure real SMTP credentials and test delivery.
- Use durable media storage for uploaded resources.
- Run migrations and collectstatic.
- Replace demonstration passwords.
- Keep DJANGO_ADMIN_PATH private.
- Enable HSTS only after HTTPS works correctly.

The archived browser-only prototype remains under legacy/ for reference. Django
serves the active application from library/, templates/library/, and
library/static/library/.
