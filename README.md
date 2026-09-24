# ATLAS Digital Repository

ATLAS is a role-aware digital repository for guests, students, teachers, and
administrators. Django owns authentication, permissions, validation, catalog
records, protected resource views, announcements, contact messages, staff activity history,
website-usage analytics, and the administrator AI Detection service.

The active interface is server-rendered HTML and CSS with presentation-only
JavaScript. Node.js is not required.

## Main features

### Guests, students, and teachers

- Browse and search the connected digital repository. Filters and sorting update automatically.
- Sort resources by title A-Z/Z-A, author A-Z/Z-A, or publication date newest/oldest.
- See each resource's title, author, file format, description or abstract, publication date, and system-added date.
- View published announcements on both the Announcements page and the Digital Repository page.
- Submit support messages to atlastshs@gmail.com.
- Register and sign in as a student or teacher.
- Read PDF or Word Resource abstracts inside ATLAS as a guest or member; authenticated readers can also save Bookmarks.

### Administrators

- Create, edit, and delete repository resource records.
- Optionally attach a validated JPG, PNG, or WebP cover and upload one required,
  protected PDF or Word (.docx) Resource abstract for each new resource.
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

The default `fast` engine performs a local, memory-safe writing-pattern review
without downloading a model. It reports AI likelihood, human likelihood,
classification confidence, the analyzed text-section count, detector name, and
detector version. PDF and Word extraction stops after the 20,000-character
analysis limit instead of parsing the rest of a large document.

The detector is wrapped by `AIDetectionService`, so operators with a larger
server can set `AI_DETECTION_ENGINE=transformer` to use the configured Vanguard
model without changing the view or template. An optional
`desklib/ai-text-detector-academic-v1.01` validator can provide a second,
academic-domain estimate. It is disabled by default because enabling both
models substantially increases memory and disk requirements.

ATLAS stores the analysis score, source label, detector identifier, model
revision, reviewer, and analysis date for reproducibility. Submitted text and
uploaded document contents are not retained in the analysis record. Detector
results can include false positives and false negatives, cannot prove
authorship, and must not be used as the sole basis for an academic decision.

## Interface behavior

The welcome greeting displays a non-email username. For accounts whose stored
username is an email address, ATLAS uses the full name or only the part before
the @ sign so the complete email is never shown in the greeting.

Catalog collection, catalog sorting, announcement category, administrator
account type, account order, and usage date filters submit automatically when a
selection changes. Search fields submit 450 milliseconds after typing stops.
The Clear or Reset link removes the active filters; there is no Apply button.

File controls show the selected or dropped filename and size. The resource and
AI analysis forms display real browser upload progress followed by a
separate server-processing state. Page navigation uses a responsive skeleton
loader, while bookmarks update optimistically and roll back automatically if
the server rejects the request. All three behaviors retain normal non-JavaScript
form and navigation fallbacks.

The top-level Display menu provides persistent Large text and High contrast
options on every page. It is keyboard accessible and keeps these controls out
of the footer so they remain easy to find on desktop and mobile layouts.

Registration enforces a password of at least six characters containing at
least one number and one special character. A live checklist confirms each
requirement, verifies that both password fields match, and displays a strength
indicator without sending or storing the typed password. Login shows only the
six-character minimum and returns a clear, account-safe incorrect-credentials
message.

The administrator account table displays each account's creation date and can
sort newest-to-oldest or oldest-to-newest. Administrators can create student or
teacher accounts from the portal. Additional administrator accounts must be
created with createsuperuser or Django Admin.

New announcements are saved as drafts and remain hidden from guests, students,
and teachers. After an administrator reviews and publishes one, it appears on
their Announcement and Digital Repository pages. Other is available as a category.

The Digital Repository page also shows the newest published announcements and links each
one to its full announcement. Administrator create, edit, publish, unpublish,
and delete actions use Django's POST-redirect-GET flow, so the returned page
already contains the saved state without requiring a manual refresh.

## Digital repository resource records

The branded resource form accepts one required Resource abstract in PDF (.pdf)
or Word (.docx) format, up to 10 MB. It also accepts an optional Cover image
(JPG, PNG, or WebP, up to 5 MB). Resource abstract format is a visible PDF/Word
toggle. The former full Resource upload, file size, and external URL are not
part of new resource entry or editing. Older database columns are retained
internally only so an upgrade cannot destroy legacy data; they are hidden from
the branded staff form and Django Admin.

Use Details for a short text description or summary. The required Resource
abstract is displayed through ATLAS's protected text reader; the original
upload is not offered as a download. Cover images are delivered
inline through a controlled Django endpoint because direct /media/ routing
remains disabled. Guests, students, teachers, and administrators see covers
and Resource abstract actions in the connected catalog and resource-detail pages.

Publication date requires a month and year and accepts an optional day. If the
day is omitted, ATLAS stores the first day of that month internally while
displaying only the month and year. Created at is the automatic date and time
when the record entered ATLAS.

Guests, students, and teachers do not receive a file-download or full-resource
action. The Read resource abstract action extracts text on the server and
displays it inside ATLAS without serving the original upload. Direct /media/
routing is disabled even in development, so uploaded repository files are not
public URLs. PDF and .docx text are supported; image-only PDFs
need OCR, and legacy .doc files should be replaced with .docx for protected
reading. Resource viewing history records the resource, visitor, account type,
and first/last view time, while refreshes within the active session are
deduplicated.

## Technology

- Python 3.12
- Django
- PostgreSQL through DATABASE_URL
- Private Cloudflare R2 media storage through django-storages (optional locally)
- django-allauth for email identity, verification, and password recovery
- WhiteNoise for deployed static assets
- pypdf for PDF text extraction
- python-docx for Word (.docx) text extraction
- Pillow for cover-image validation
- PyTorch for local CPU model inference
- Hugging Face Transformers for replaceable local text detectors
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

The default fast AI Detection engine starts immediately and does not download a
model. If `AI_DETECTION_ENGINE=transformer` is selected, the first analysis
downloads and caches the public Vanguard model from Hugging Face. Its weights
are about 1.6 GB, so transformer mode requires a larger server and can take
several minutes on its first request. If academic validation is enabled, its
model is downloaded and cached separately and requires substantial additional
memory and disk space.

Registration and role-aware login are available at /register/ and /login/.
django-allauth account management is mounted under /accounts/.
Teacher registration and teacher sign-in accept official `@deped.gov.ph`
addresses only. Student accounts may use another active address that can receive
the verification email.

## Start from VS Code

The repository contains a Windows one-key launcher and matching VS Code tasks.

- Press **Ctrl+Shift+B** to prepare the environment, migrate a private local
  SQLite database, start ATLAS, and open it in your default browser.
- Double-click **START_ATLAS.cmd** for the same quick-start experience without
  opening VS Code.
- Press Ctrl+Shift+P, choose Tasks: Run Task, then select
  **ATLAS: Start with configured database** when you want to use PostgreSQL
  from `.env` instead of the quick-start database.
- Press F5 and select ATLAS: Start Django to run with the debugger.
- Without VS Code, run:

  ```powershell
  powershell -ExecutionPolicy Bypass -File .\scripts\start_atlas.ps1 -UseSQLite -OpenBrowser
  ```

The first run creates .venv and installs dependencies. Later runs reinstall
only when requirements.txt changes. The script always runs Django with the
virtual-environment interpreter and applies pending migrations before starting
the server. This avoids using a different global Python installation. Quick
Start stores local-only data in the ignored `db.sqlite3` file; deployment and
the configured-database task continue to use `DATABASE_URL` from `.env`.

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
TEACHER_EMAIL_DOMAINS=deped.gov.ph
```

`TEACHER_EMAIL_DOMAINS` is a comma-separated allowlist. Keep the default for a
DepEd-only teacher portal; any listed domain and its subdomains are accepted.

For a hosted PostgreSQL service, use the provider's complete connection URL and
set DB_SSL_REQUIRE=True when TLS is required.

AI Detection model selection is environment-based:

```dotenv
AI_DETECTION_ENGINE=fast
AI_DETECTION_PRIMARY_MODEL=ShantanuT01/vanguard-ai-text-detector
AI_DETECTION_PRIMARY_REVISION=823061be63b90f2b42f64ac1e1f82772e872533b
AI_DETECTION_ENABLE_VALIDATION=False
AI_DETECTION_VALIDATION_MODEL=desklib/ai-text-detector-academic-v1.01
AI_DETECTION_VALIDATION_REVISION=main
HF_HUB_DISABLE_XET=1
HF_HUB_DISABLE_SYMLINKS_WARNING=1
```

Keep `AI_DETECTION_ENGINE=fast` for small Render instances. Set it to
`transformer` only when the service has enough memory for the configured model.
Use a Hugging Face commit hash instead of `main` for a release that must always
load the same weights. When validation is enabled, ATLAS runs both configured
detectors and records the secondary result with the primary analysis. The Hub
settings use the standard resumable HTTP downloader on Windows and suppress the
non-fatal symlink-cache warning; operators can explicitly set
`HF_HUB_DISABLE_XET=0` after confirming Xet works on their network.

## Private Cloudflare R2 storage

ATLAS can keep uploaded cover images and resource abstracts in a private R2
bucket. Static CSS and JavaScript remain on WhiteNoise. Create a new R2 API
token with Object Read & Write access limited to the ATLAS bucket, then add the
new S3 credentials to the private `.env` file or the hosting provider's secret
settings:

```dotenv
R2_STORAGE_ENABLED=True
R2_ACCOUNT_ID=your-32-character-account-id
R2_ACCESS_KEY_ID=your-new-access-key-id
R2_SECRET_ACCESS_KEY=your-new-secret-access-key
R2_BUCKET_NAME=your-bucket-name
R2_ENDPOINT_URL=https://your-account-id.r2.cloudflarestorage.com
R2_SIGNED_URL_EXPIRY=300
```

The endpoint is account-level; do not append `/bucket-name`. Files stay private
and generated object URLs are signed for a short period. ATLAS normally reads
protected files through its authenticated Django endpoints, so browser CORS is
not required for the current server-mediated upload and reader flow.

Verify the active backend and then perform a temporary write/read/delete test:

```powershell
python manage.py check_storage
python manage.py check_storage --write-test
```

Keep `R2_STORAGE_ENABLED=False` for local filesystem storage. Existing files in
`media/` are not copied automatically when R2 is enabled; upload them to the
same object keys before switching an installation that already contains media.

## Contact details and email delivery

The public Contact page and site footer use the configured support email and
optionally show a click-to-call phone number. Contact submissions are addressed
to atlastshs@gmail.com. Each message
contains the visitor's name, submitted email, authenticated account email when
available, subject, and message. Reply-To is set to the visitor's submitted
email.

The console backend is safe for local development but prints messages instead
of delivering them:

```dotenv
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
SUPPORT_EMAIL=atlastshs@gmail.com
SUPPORT_HOURS=Monday–Friday, 8:00 AM–5:00 PM
SUPPORT_PHONE=+63 912 345 6789
```

For real Gmail delivery, create a Google App Password and use:

```dotenv
ACCOUNT_EMAIL_VERIFICATION=mandatory
ACCOUNT_EMAIL_SUBJECT_PREFIX="[A.T.L.A.S.] "
ACCOUNT_DEFAULT_HTTP_PROTOCOL=https
SITE_ID=1
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DEFAULT_FROM_EMAIL=ATLAS <atlastshs@gmail.com>
SUPPORT_EMAIL=atlastshs@gmail.com
SUPPORT_PHONE=+63 912 345 6789
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_TIMEOUT=20
EMAIL_HOST_USER=atlastshs@gmail.com
EMAIL_HOST_PASSWORD=your-google-app-password
```

Do not use the normal Gmail password or leave the example password in place.
For Gmail, enable two-step verification and create an App Password. If delivery
fails, ATLAS keeps the form visible, shows an error, and does not retain a new
unverified account or record a contact message as successfully sent. Switch back
to the console backend while developing locally; verification links will be
printed in the terminal running Django.

After adding a new App Password, verify the SMTP login and send one real test
message before testing registration:

```powershell
python manage.py verify_email --to your-test-address@example.com
```

The command never prints SMTP credentials. It refuses the console, dummy, and
in-memory test backends so a successful result confirms use of a delivery
backend. Registration verification, verification resends, password recovery,
and Contact-page delivery then use the same tested connection settings.

Production uses Site ID 1 (`atlas-repository.onrender.com`) and HTTPS account
links. Configure these private Render environment values:

```dotenv
SITE_ID=1
ACCOUNT_DEFAULT_HTTP_PROTOCOL=https
```

For optional local links, create Site ID 2 once and then use `SITE_ID=2` with
`ACCOUNT_DEFAULT_HTTP_PROTOCOL=http` in the ignored local `.env` file:

```powershell
python manage.py shell -c "from django.contrib.sites.models import Site; site, created = Site.objects.update_or_create(id=2, defaults={'domain': '127.0.0.1:8000', 'name': 'A.T.L.A.S. Local Development'}); Site.objects.clear_cache(); print(site.domain)"
```

The Render build command runs `python manage.py migrate --noinput` before the
deployment-readiness check, so committed data migrations configure the Site
record in the attached Render PostgreSQL database during deployment.

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
- Service and presenter classes own reusable business logic, queries, and
  display-safe configuration formatting.
- Middleware delegates session tracking to a service object.
- Views use replaceable service-class attributes for testability.

Dependencies flow from views and middleware to services and models. Models do
not import templates or views.

```text
atlas/
|-- settings.py                         Environment-based Django configuration
+-- urls.py                             Root routing and private Django Admin

accounts/
|-- apps.py                             Account-domain Django configuration
+-- urls.py                             Authentication and user-management routes

repository/
|-- apps.py                             Repository-domain Django configuration
+-- urls.py                             Catalog, bookmark, reader, and resource CRUD routes

ai_detection/
|-- apps.py                             AI-domain Django configuration
+-- urls.py                             Protected AI Detection route

library/
|-- models.py                           Domain entities and persistence rules
|-- forms.py                            Authentication, content, contact, and AI input forms
|-- middleware.py                       Thin request/response integration
|-- services/
|   |-- activity.py                     ActivityRecorder
|   |-- ai_detection.py                 AIDetectionService and detector adapters
|   |-- catalog.py                      CatalogQueryService
|   |-- contact.py                      ContactEmailService
|   |-- context.py                      GreetingNameResolver, PageContextBuilder,
|   |                                    and SupportContactPresenter
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
announcement category, Bookmark display names, and resource-view history.
Migration 0007 adds cover-image and abstract-file storage to repository resources.
Migration 0008 safely renames the abstract field to Resource abstract without
deleting existing uploads. Migration 0009 adds reproducibility metadata for AI
Detection analyses without storing submitted content. Migration 0010 adds
age/guardian consent and privacy-request classification. Do not manually add
or rename these columns; Django migrations handle both new and existing
installations.

## Important commands

```powershell
python manage.py check
python manage.py check_database
python manage.py makemigrations --check --dry-run
python manage.py verify_deployment
python manage.py check_storage
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

ATLAS includes a public Privacy Policy and Terms page, consent-gated optional
usage analytics, `robots.txt`, an HTTPS sitemap, themed HTTP error pages, GZip
responses, and automatic WebP optimization for new cover uploads. Essential
session and CSRF cookies remain available when a visitor declines optional
analytics.

The policy page also publishes service/operator contact details, a third-party
dependency inventory, data-minimization practices, minor/guardian consent,
accessibility features, open-source and uploaded-image licensing rules, email
choices, and transparent statements about fees, reviews, and automated claims.
ATLAS has no payment workflow. Privacy requests are classified in the Contact
form, and users can submit access, correction, email-preference, or data
deletion requests with explicit form consent. Configure `BUSINESS_NAME`,
`BUSINESS_OPERATOR`,
`BUSINESS_ADDRESS`, `BUSINESS_COUNTRY`, `BUSINESS_SERVICE_TYPE`, and
`DATA_PRIVACY_EMAIL` with the responsible institution's exact details before
public launch.

Fixed-window rate limits protect general traffic, sign-in, registration,
contact, password-reset/email actions, and AI Detection. The included Procfile
uses one worker, so Django's default in-memory cache applies these limits
consistently. A deployment with multiple workers or application instances must
configure a shared atomic cache (for example Redis); otherwise each instance
maintains a separate counter. Set `RATE_LIMIT_TRUST_PROXY=True` only when the
application is behind a trusted proxy that replaces `X-Forwarded-For`.

Linux deployment platforms can start ATLAS with the included `Procfile`. It
uses one Gunicorn worker with four threads so the lazily loaded detector weights
are held once per application instance instead of being duplicated across
multiple worker processes. Before starting a new release, run:

```powershell
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
python manage.py verify_deployment
```

Copy `.env.production.example` into the hosting provider's private environment
configuration and replace every placeholder. `verify_deployment` applies
Django's deployment checks, ATLAS-specific checks, a live PostgreSQL query, and
an unapplied-migration check. The public `/health/` endpoint performs a minimal
database readiness check for a load balancer without exposing database names,
users, credentials, or AI model details. It deliberately does not load the
large AI model during routine health polling.

For a Linux hosting provider with a build-command field, use:

```bash
bash build.sh
```

The script installs the locked dependencies, collects static assets, applies
database migrations, and runs the complete production verification command.
The deployment stops instead of launching with placeholder email, security,
database, storage, or institution settings. The `Procfile` then starts the web
process with Gunicorn.

### Render deployment

ATLAS pins Python 3.12.10 in `.python-version` because Render's default Python
version can change. Create a **Python 3 Web Service** from this repository and
configure:

```text
Build Command: bash build.sh
Start Command: gunicorn atlas.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 300 --access-logfile -
Health Check Path: /health/
```

Create or attach Render PostgreSQL and copy its complete **internal database
URL** into `DATABASE_URL`. The value must start with `postgresql://`; do not
enter backslashes or the literal `USERNAME`, `PASSWORD`, `HOST`, or
`DATABASE_NAME` placeholders.

Render automatically supplies `RENDER_EXTERNAL_HOSTNAME`. ATLAS adds that host
and its HTTPS origin to Django's allowed-host and CSRF configuration. Only add
`DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS` yourself when using a
custom domain.

Add every non-placeholder value from `.env.production.example` in Render's
Environment page. In particular, configure the R2 credentials, Gmail App
Password, private administrator path, business/privacy details, HTTPS flags,
and AI cache path as private environment variables. Never upload `.env` or
paste secrets into the Git repository.

On Windows Server, use the installed Waitress server instead:

```powershell
waitress-serve --listen=0.0.0.0:8000 atlas.wsgi:application
```

The AI model cache must be stored on persistent disk in production. If the
hosting platform has an ephemeral filesystem, set `HF_HOME` to a mounted
persistent directory; otherwise each new instance may download the model again.

```dotenv
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=repository.example.edu
DJANGO_CSRF_TRUSTED_ORIGINS=https://repository.example.edu
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
DB_SSL_REQUIRE=True
RATE_LIMIT_ENABLED=True
RATE_LIMIT_TRUST_PROXY=True
```

Also:

- Use a unique production DJANGO_SECRET_KEY.
- Set the platform's `PORT` variable or allow the Procfile default of 8000.
- Configure real SMTP credentials and test delivery.
- Enable and verify private Cloudflare R2 storage for production uploads.
- Run migrations and collectstatic.
- Replace demonstration passwords.
- Keep DJANGO_ADMIN_PATH private.
- Confirm `/robots.txt`, `/sitemap.xml`, and `/privacy-and-terms/` use the final
  production hostname.
- Have the responsible institution review the policy wording and retention
  practices before public launch.
- Enable HSTS and HSTS preload only after HTTPS works correctly for the main
  domain and every subdomain; browser preload enrollment is difficult to undo.

The active Django application uses accounts/, repository/, and ai_detection/
as feature entry points. Shared models, views, services, templates, and static
assets remain under library/ to preserve the existing database migration and
URL compatibility contracts.
