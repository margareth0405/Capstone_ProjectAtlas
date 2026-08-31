# ATLAS Django e-Library

ATLAS is a role-aware digital library for guests, students, teachers, and
administrators. Django owns authentication, permissions, validation, catalog
records, protected resource views, announcements, contact messages, staff activity history,
website-usage analytics, and the administrator AI Detection service.

The active interface is server-rendered HTML and CSS with presentation-only
JavaScript. Node.js is not required.

## Main features

### Guests, students, and teachers

- Browse and search the connected library catalog. Filters and sorting update automatically.
- Sort resources by title A-Z/Z-A, author A-Z/Z-A, or publication date newest/oldest.
- See each resource's title, author, file format, description or abstract, publication date, and system-added date.
- View published announcements on both the Announcements page and the Library page.
- Submit support messages to atlastshs@gmail.com.
- Register and sign in as a student or teacher.
- Read extractable PDF or Word content inside ATLAS as a guest or member; authenticated readers can also save Bookmarks.

### Administrators

- Create, edit, and delete PDF or Word library resources.
- Enter a publication month and year, with an optional exact day; ATLAS records the system-added date automatically.
- Save announcements as drafts, review them, then publish, unpublish, edit, or delete them. The administrator form contains only title, body, and category, including Other.
- Create student and teacher accounts.
- Search accounts by name or email.
- Filter accounts by student, teacher, or administrator.
- Sort accounts from newest to oldest or oldest to newest.
- Delete reader accounts while protecting the active administrator and
  superusers.
- Review which guest, student, teacher, or administrator opened each protected resource.
- Review a dated audit history of resource, account, and announcement actions.
- Review a responsive side-by-side website-usage chart and searchable visit history by date and account type, including active time, sessions, distinct visitors, deduplicated page views, and each session's last page.
- Analyze pasted text, PDF files, and Word (.docx) files with the
  administrator-only AI Detection service.

AI Detection accepts pasted text from 100 to 20,000 characters or one PDF or
Word (.docx) document up to 10 MB. Uploads are processed in memory and are not
saved. Scanned image-only PDFs must go through OCR first.

The AI Detection page and its Administrator Portal entry use the same white
panels, maroon accents, controls, and responsive spacing as the rest of ATLAS.

The service runs the local
`openai-community/roberta-base-openai-detector` model through Hugging Face
Transformers and reports AI likelihood, human likelihood, model confidence,
and the number of analyzed text sections. Longer submissions are split into
250-word sections so the analysis is not limited to the beginning.

This model was trained to distinguish English human writing from output
created by GPT-2. It is not a universal detector for current AI systems, cannot
prove authorship, and must not be used as the sole basis for an academic
decision.

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

New announcements are saved as drafts and remain hidden from guests, students,
and teachers. After an administrator reviews and publishes one, it appears on
their Announcement and Library pages. Other is available as a category.

The Library page also shows the newest published announcements and links each
one to its full announcement. Administrator create, edit, publish, unpublish,
and delete actions use Django's POST-redirect-GET flow, so the returned page
already contains the saved state without requiring a manual refresh.

## Library resource records

The branded resource form accepts one uploaded PDF (.pdf) or Word (.docx)
file. File format is a visible PDF/Word toggle. File size and external URL are
not part of new resource entry or editing. Older database columns are retained
internally only so an upgrade cannot destroy legacy data; they are hidden from
the branded staff form and Django Admin.

Use Details for a short description or abstract. Publication date requires a
month and year and accepts an optional day. If the day is omitted, ATLAS stores
the first day of that month internally while displaying only the month and
year. Created at is the automatic date and time when the record entered ATLAS.

Guests, students, and teachers do not receive a file-download action. The Read
resource action extracts text on the server and displays it inside ATLAS without
serving the original upload. Direct /media/ routing is disabled even in development so uploaded library files are not public URLs. PDF and .docx text are supported; image-only PDFs
need OCR, and legacy .doc files should be replaced with .docx for protected
reading. Resource viewing history records the resource, visitor, account type,
and first/last view time, while refreshes within the active session are
deduplicated.

## Technology

- Python 3.12
- Django
- PostgreSQL through DATABASE_URL
- django-allauth for email identity, verification, and password recovery
- WhiteNoise for deployed static assets
- pypdf for PDF text extraction
- python-docx for Word (.docx) text extraction
- PyTorch for local CPU model inference
- Hugging Face Transformers for the local RoBERTa detector
- HTML, CSS, Bootstrap-compatible markup, and presentation JavaScript

## Local setup on Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env with your PostgreSQL and administrator-path settings.
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000/. PostgreSQL must be running and DATABASE_URL must
point to an existing database before running Django commands.

The first AI Detection analysis downloads and caches the public RoBERTa model
from Hugging Face. Its PyTorch/Safetensors weights are approximately 500 MB, so
the first analysis can take several minutes. Later analyses use the local cache
and do not require an API key, account, or per-scan payment.

Registration and role-aware login are available at /register/ and /login/.
django-allauth account management is mounted under /accounts/.

## Start from VS Code

The repository contains a Windows startup script and matching VS Code tasks.

- Press Ctrl+Shift+P, choose Tasks: Run Task, and select
  ATLAS: Start Django.
- Press Ctrl+Shift+B to use the default build task.
- Press F5 and select ATLAS: Start Django to run with the debugger.
- Without VS Code, run:

  ```powershell
  powershell -ExecutionPolicy Bypass -File .\scripts\start_atlas.ps1
  ```

The first run creates .venv and installs dependencies. Later runs reinstall
only when requirements.txt changes. The script always runs Django with the
virtual-environment interpreter and applies pending migrations before starting
the server. This avoids using a different global Python installation.

## Environment configuration

Copy .env.example to .env. Never commit the real .env file or any database
password, Django secret, or Gmail App Password.

Minimum development settings:

```dotenv
DJANGO_SECRET_KEY=replace-with-a-long-random-secret
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_ADMIN_PATH=replace-with-a-private-admin-path
DATABASE_URL=postgresql://atlas_user:strong-password@localhost:5432/atlas
DB_SSL_REQUIRE=False
```

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

```dotenv
DJANGO_EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
SUPPORT_EMAIL=atlastshs@gmail.com
SUPPORT_HOURS=Monday–Friday, 8:00 AM–5:00 PM
```

For real Gmail delivery, create a Google App Password and use:

```dotenv
DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DEFAULT_FROM_EMAIL=ATLAS <atlastshs@gmail.com>
SUPPORT_EMAIL=atlastshs@gmail.com
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=atlastshs@gmail.com
EMAIL_HOST_PASSWORD=your-google-app-password
```

Do not use the normal Gmail password. If delivery fails, ATLAS keeps the form
visible, shows an error, and does not record the message as successfully sent.

## Administrator setup

The administrator login is intentionally absent from public navigation.

1. Set a private DJANGO_ADMIN_PATH value in .env.
2. Apply migrations and create a superuser:

   ```powershell
   python manage.py migrate
   python manage.py createsuperuser
   ```

3. Start Django and open:

   ```text
   http://127.0.0.1:8000/<DJANGO_ADMIN_PATH>/
   ```

4. After signing in, open /staff/ for the branded Administrator Portal.

The staff account form creates students and teachers only. Create additional
administrators through createsuperuser or Django Admin.

## Optional development data

The idempotent command below creates catalog records, announcements, and reader
accounts:

```powershell
python manage.py seed_atlas
```

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

```text
atlas/
|-- settings.py                         Environment-based Django configuration
+-- urls.py                             Root routing and private Django Admin

library/
|-- models.py                           Domain entities and persistence rules
|-- forms.py                            Authentication, content, contact, and AI input forms
|-- middleware.py                       Thin request/response integration
|-- services/
|   |-- activity.py                     ActivityRecorder
|   |-- ai_detection.py                 RobertaAIDetector
|   |-- catalog.py                      CatalogQueryService
|   |-- contact.py                      ContactEmailService
|   |-- context.py                      GreetingNameResolver and PageContextBuilder
|   |-- documents.py                    DocumentTextExtractor
|   |-- navigation.py                   SafeRedirectService
|   |-- staff_portal.py                 StaffUserDirectory, UsageAnalytics,
|   |                                    and StaffPortalContextService
|   |-- usage.py                        WebsiteUsageTracker
|   +-- resource_views.py                ResourceViewTracker
|-- views/
|   |-- authentication.py               Registration, login, guest, and logout
|   |-- catalog.py                      Catalog, bookmarks, and protected reading
|   |-- public.py                       Dashboard, announcements, contact, and usage heartbeat
|   |-- mixins.py                       Context and staff permission mixins
|   |-- staff.py                        Stable administrator-view import facade
|   |-- staff_dashboard.py              Administrator homepage
|   |-- staff_crud.py                   Resource and announcement CRUD
|   |-- staff_accounts.py               Account creation and deletion
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
```

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

A new navigation records a page view once. Browser reload detection and a
session-level last-location guard prevent refreshes from increasing page views.
A lightweight heartbeat is sent every 45 seconds only while an ATLAS page is
visible and online. Active time is based on those visible heartbeats, sessions
split after 15 idle minutes or at a local-calendar day boundary, and guest
visitors are counted by distinct browser session. Tracking does not inspect
keystrokes, other websites, background applications, or activity outside
ATLAS. Historical rows created before migration 0004 have zero page views and
no last-page value because those values cannot be reconstructed.

### Activity, visit, and resource-view history

| Record | Purpose |
| --- | --- |
| Activity history | Audits important resource, account, and announcement changes, including the responsible administrator. |
| Website visit history | Stores session start, last visible activity, active seconds, deduplicated page views, last page, role, and date. It can be searched by visitor and filtered by account type. |
| Resource viewing history | Records who opened a specific protected resource, their account type, and the first/last view time. Repeated refreshes inside the 15-minute active window update one record. |

The former download endpoint and Download history panel are no longer active.
Existing legacy database rows are left intact during upgrade to avoid
destructive data loss, but ATLAS does not create or expose new download records.
ActivityRecorder creates new audit entries at the time an action occurs. Events
from before the audit feature was installed are not reconstructed retroactively.

## Database updates required for this version

Run migrations after pulling or copying these changes:

```powershell
python manage.py migrate
```

Migration 0003 adds administrator activity and website-visit history. Migration
0004 adds page-view counts and last-page tracking. Migration 0005 adds resource
publication dates and PDF/Word format choices. Migration 0006 adds the Other
announcement category, Bookmark display names, and resource-view history. Do not manually add these columns; Django migrations handle
both new and existing installations.

## Important commands

```powershell
python manage.py check
python manage.py check_database
python manage.py makemigrations --check --dry-run
python manage.py test
python manage.py collectstatic --noinput
```

Focused announcement, catalog, resource, and administrator tests:

```powershell
python manage.py test library.tests.test_staff_views library.tests.test_public_views library.tests.test_staff_features
```

## Troubleshooting missing Python modules

Use the project interpreter for every Django command:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
```

If PowerShell reports No module named django, allauth, docx, pypdf, psycopg,
torch, transformers, whitenoise, or dotenv, the command is using the wrong interpreter or the
requirements were not installed. Run the commands above, or use
scripts\start_atlas.ps1, which selects .venv automatically. Do not install a
package named docx; the correct dependency is python-docx.

## Production checklist

```dotenv
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=library.example.edu
DJANGO_CSRF_TRUSTED_ORIGINS=https://library.example.edu
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
DB_SSL_REQUIRE=True
```

Also:

- Use a unique production DJANGO_SECRET_KEY.
- Configure real SMTP credentials and test delivery.
- Use durable private media storage for uploaded resources; do not map MEDIA_ROOT to a public web-server URL.
- Run migrations and collectstatic.
- Replace demonstration passwords.
- Keep DJANGO_ADMIN_PATH private.
- Enable HSTS only after HTTPS works correctly.

The archived browser-only prototype remains under legacy/ for reference. Django
serves the active application from library/, templates/library/, and
library/static/library/.
