# ATLAS load tests

These k6 tests implement the staged plan from the performance-testing brief while
using ATLAS's real routes and role-aware login form.

## Prerequisites

Install k6, start ATLAS, and create a dedicated account pool. Never use an
administrator account or real student credentials.

```powershell
$env:ATLAS_LOAD_TEST_PASSWORD = "replace-with-a-strong-test-password"
.\.venv\Scripts\python.exe manage.py create_load_test_users --count 100
.\.venv\Scripts\python.exe manage.py runserver
```

The account command creates verified student accounts named
`loadtest001@example.com` through `loadtest100@example.com`. It is idempotent and
reads the password from the environment so the credential is not committed or
placed in shell history.

## Run in stages

Start with the anonymous/public smoke test:

```powershell
k6 run -e LOAD_PROFILE=smoke -e BASE_URL=http://127.0.0.1:8000 .\load_tests\atlas-full-test.js
```

Then run authenticated student sessions:

```powershell
$env:TEST_PASSWORD = $env:ATLAS_LOAD_TEST_PASSWORD
k6 run -e LOAD_PROFILE=smoke -e BASE_URL=http://127.0.0.1:8000 -e TEST_PASSWORD=$env:TEST_PASSWORD .\load_tests\atlas-authenticated-test.js
```

After each profile passes, repeat with `normal`, `busy`, and `peak`. The profiles
represent 10, 25, 50, and 100 concurrent users. `stress` ramps from 100 to 150
users and requires a 150-account pool:

```powershell
.\.venv\Scripts\python.exe manage.py create_load_test_users --count 150
k6 run -e LOAD_PROFILE=stress -e TEST_USER_COUNT=150 -e BASE_URL=http://127.0.0.1:8000 -e TEST_PASSWORD=$env:TEST_PASSWORD .\load_tests\atlas-authenticated-test.js
```

The authenticated test assigns one numbered account to each virtual user. It
refuses to run when the selected profile is larger than `TEST_USER_COUNT`, unless
`ALLOW_SHARED_ACCOUNTS=true` is deliberately supplied.

The `busy` profile is the release gate for ATLAS's 30-50 concurrent-user target.
Run both public and authenticated variants against staging before release. Both
must finish with zero 429 responses, zero 5xx responses, a failed-request rate
below 1%, and p95 response time below two seconds. A passing local run confirms
application behavior; a staging run is still required to verify the actual web,
database, network, and object-storage plans.

## Optional resource-reader coverage

Repository listing, search, resource detail, dashboard, bookmarks, and
announcements are included. Protected document extraction is opt-in because it
can exercise object storage and document parsers much more heavily:

```powershell
k6 run -e LOAD_PROFILE=smoke -e TEST_PASSWORD=$env:TEST_PASSWORD -e TEST_RESOURCE_READER=true -e RESOURCE_ID=1 .\load_tests\atlas-authenticated-test.js
```

Use an existing resource ID with a valid resource abstract. ATLAS has no active
download endpoint, so the test exercises the protected in-browser abstract
reader instead of inventing a download URL.

## Authorized remote testing

Remote targets are blocked by default. Only load-test a deployment you own or
have explicit permission to test. After confirming authorization, opt in:

```powershell
k6 run -e LOAD_PROFILE=smoke -e BASE_URL=https://your-authorized-host.example -e ALLOW_REMOTE=true .\load_tests\atlas-full-test.js
```

Run the profiles sequentially and review errors before increasing traffic. For
each formal run, retain checks, request duration (average, median, p90, p95,
maximum), failed-request rate, total requests, iterations, iteration duration,
VUs, and the 403/404/429/5xx counters. Avoid load-testing registration, password
reset, email verification, uploads, and AI analysis at 100 users; those need
smaller, separately authorized scenarios.
