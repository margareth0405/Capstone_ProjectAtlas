# ATLAS Django e-Library

ATLAS is a role-aware digital library for guests, students, teachers, and
administrators. Django owns authentication, permissions, validation, catalog
records, downloads, announcements, contact messages, staff activity history,
website-usage analytics, and the administrator AI Detection service.

The active interface is server-rendered HTML and CSS with presentation-only
JavaScript. Node.js is not required.

## Main features

### Guests, students, and teachers

- Browse, search, filter, and sort the library catalog. Search and filter changes apply automatically.
- View published announcements.
- Submit support messages to atlastshs@gmail.com.
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
- Review website usage by role and date, including active time, sessions, visitors, page views, and each session's last page.
- Analyze pasted text, PDF files, and Word (.docx) files with the
  administrator-only AI Detection service.

AI Detection accepts pasted text from 100 to 20,000 characters or one PDF or
Word (.docx) document up to 10 MB. Uploads are processed in memory and are not
saved. Scanned image-only PDFs must go through OCR first.

The AI Detection page and its Administrator Portal entry use the same white
panels, maroon accents, controls, and responsive spacing as the rest of ATLAS.

The service reports explainable writing-pattern indicators such as vocabulary
diversity, sentence-length variation, and repeated phrases. It cannot prove who
or what authored a document and must not be used as the sole basis for an
academic decision.

## Interface behavior

The welcome greeting displays a non-email username. For accounts whose stored
username is an email address, ATLAS uses the full name or only the part before
the @ sign so the complete email is never shown in the greeting.

Catalog collection, catalog sorting, announcement category, administrator
account type, account order, and usage date filters submit automatically when a
selection changes. Search fields submit 450 milliseconds after typing stops.
The Clear or Reset link removes the active filters; there is no Apply button.

The administrator account table displays each account's creation date and can
sort newest-to-oldest or oldest-to-newest. Administrators can create student or
teacher accounts from the portal. Additional administrator accounts must be
created with createsuperuser or Django Admin.

Published announcements created in the Administrator Portal appear on the
announcement pages used by guests, students, and teachers. Draft announcements
remain hidden from non-staff users.
## Technology

- Python 3.12
- Django
- PostgreSQL through DATABASE_URL
- django-allauth for email identity, verification, and password recovery
- WhiteNoise for deployed static assets
- pypdf for PDF text extraction
- python-docx for Word (.docx) text extraction
- HTML, CSS, Bootstrap-compatible markup, and presentation JavaScript

## Local setup on Windows PowerShell

~~~powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
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
  powershell -ExecutionPolicy Bypass -File .\scripts\start_atlas.ps1
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

The public Contact page lists email only; it does not display a phone number.
Contact submissions are addressed to atlastshs@gmail.com. Each message
contains the visitor's name, submitted email, authenticated account email when
available, subject, and message. Reply-To is set to the visitor's submitted
email.

The console backend is safe for local development but prints messages instead
of delivering them:

~~~dotenv
DJANGO_EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
SUPPORT_EMAIL=atlastshs@gmail.com
SUPPORT_HOURS=Monday–Friday, 8:00 AM–5:00 PM
~~~

For real Gmail delivery, create a Google App Password and use:

~~~dotenv
DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DEFAULT_FROM_EMAIL=ATLAS <atlastshs@gmail.com>
SUPPORT_EMAIL=atlastshs@gmail.com
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=atlastshs@gmail.com
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
|-- forms.py                            Authentication, content, contact, and AI input forms
|-- middleware.py                       Thin request/response integration
|-- services/
|   |-- activity.py                     ActivityRecorder
|   |-- ai_detection.py                 WritingPatternAnalyzer
|   |-- catalog.py                      CatalogQueryService
|   |-- contact.py                      ContactEmailService
|   |-- context.py                      GreetingNameResolver and PageContextBuilder
|   |-- documents.py                    DocumentTextExtractor
|   |-- navigation.py                   SafeRedirectService
|   |-- staff_portal.py                 StaffUserDirectory, UsageAnalytics,
|   |                                    and StaffPortalContextService
|   +-- usage.py                        WebsiteUsageTracker
|-- views/
|   |-- authentication.py               Registration, login, guest, and logout
|   |-- catalog.py                      Catalog, favorites, and downloads
|   |-- public.py                       Dashboard, announcements, contact, and usage heartbeat
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

WebsiteUsageMiddleware delegates tracking to WebsiteUsageTracker for signed-in
accounts and guest-mode sessions. The Administrator Portal filters each selected date using the configured local
timezone (Asia/Manila by default), with explicit start and end boundaries so a
selected past date is not mixed with today, and displays:

- Active time: time accumulated between page activity and visible-page
  heartbeats, capped at 15 minutes for one idle gap.
- Sessions: separate visits; a gap longer than 15 minutes starts a new visit.
- Visitors: distinct signed-in accounts plus individual guest sessions.
- Page views: browser navigations inside ATLAS. Refreshing/reloading the
  current page and heartbeat requests do not add page views.
- Last page: the latest ATLAS path viewed during that session.
- Account-type chart: active minutes grouped into guest, student, teacher, and
  administrator roles.

A reload-aware browser event records a page view after a new navigation. A
lightweight heartbeat is sent every 45 seconds only while an ATLAS page is
visible and the browser is online. Tracking does not inspect keystrokes, other
websites, background applications, or activity outside ATLAS. Historical rows
created before migration 0004 have zero page views and no last-page value
because those values cannot be reconstructed.

### Activity history versus download history

| Record | Purpose | What deleting the record does |
| --- | --- | --- |
| Activity history | Audits resource, account, announcement, and download create/update/delete actions, including the administrator responsible. | The portal currently treats these as audit records; it does not use them as the content itself. |
| Download history | Records which signed-in account downloaded which library resource and the exact time. | Deletes only the audit row. It does not delete the resource or account, revoke access, or remove a copy already saved by the user. |
| Website visit history | Stores session start, last activity, active seconds, page views, last page, role, and date. | Used only for the Administrator Portal usage report. |

ActivityRecorder creates new audit entries at the time an action occurs. Events
from before the audit feature was installed are not reconstructed retroactively.

## Database updates required for this version

Run migrations after pulling or copying these changes:

~~~powershell
python manage.py migrate
~~~

Migration 0003 adds administrator activity and website-visit history. Migration
0004 adds page-view counts and last-page tracking. Do not manually add these
columns to the database; Django migrations handle both new and existing
installations.
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
