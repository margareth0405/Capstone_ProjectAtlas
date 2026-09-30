# ATLAS security controls

ATLAS treats authentication, repository administration, and uploaded documents
as security-sensitive. The controls below are enforced server-side and covered
by the automated security regression workflow.

| Area | Enforced control |
| --- | --- |
| Authentication | Django sessions and password hashing, django-allauth email verification and recovery, generic credential failures, failed-login throttling, and a 12-character policy for new/reset passwords. |
| Authorization | Active staff/superuser mixins protect administrative views; hiding a button is never used as the authorization decision. |
| CSRF | Django CSRF middleware and tokens protect every state-changing browser form; secure, HTTP-only CSRF cookies are required in production. |
| Input validation | Django forms, typed model fields, explicit choice/range/length validation, safe redirect allow-listing, and ORM parameterization handle untrusted input. |
| File uploads | Extension, size, image decoding/re-encoding, PDF signature, DOCX structure, archive traversal/encryption, expansion, member-count, and compression-ratio checks run before persistence or parsing. Request bodies are capped at 30 MB by default. |
| XSS | Django template auto-escaping, text-only DOM updates for user-controlled values, `nosniff`, and an enforced Content Security Policy protect rendered pages. |
| Dependencies | Exact versions are pinned. `pip-audit` runs on pushes, pull requests, and weekly against current vulnerability advisories. |
| Production | `verify_deployment` blocks insecure Django settings, non-PostgreSQL or unavailable databases, pending migrations, public/wildcard hosts, insecure CSRF origins, local ephemeral uploads, and disabled rate limits. |
| Sensitive information | Secrets are environment-only, `.env` is ignored, custom errors hide tracebacks, health output exposes only dependency status, and private uploads use R2 in production. |
| Rate limiting | Account/session-scoped limits cover failed sign-ins, registration, email, contact, search, uploads, AI analysis, and staff mutations without grouping an entire school behind one IP. |

Before a release, run:

```powershell
python -m pip install -r requirements-audit.txt
python -m pip_audit -r requirements.txt --progress-spinner off
python manage.py test
python manage.py check --deploy
python manage.py verify_deployment
```

Run the final two commands with the real production environment and PostgreSQL
connection. Never paste credentials, private uploaded documents, or exploit
details into a public issue.
