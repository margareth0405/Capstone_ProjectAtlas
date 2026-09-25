"""Security, privacy, performance, and public-error regression coverage."""

from allauth.account.models import EmailAddress
from django.contrib.auth.models import AnonymousUser
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, override_settings
from django.urls import reverse

from library.forms import AIDetectionForm, LibraryItemForm
from library.models import ContactMessage, WebsiteVisit
from library.tests.base import LibraryTestCase
from library.views import errors


class PublicPolicyAndDiscoveryTests(LibraryTestCase):
    def test_privacy_terms_and_cookie_controls_are_public(self):
        response = self.client.get(reverse("library:privacy_terms"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Privacy Policy and Terms &amp; Conditions")
        self.assertContains(response, "Change cookie preferences")

        landing = self.client.get(reverse("library:landing"))
        self.assertContains(landing, 'id="cookieConsent"')
        self.assertContains(landing, 'data-cookie-choice="essential"')
        self.assertContains(landing, 'data-cookie-choice="analytics"')
        self.assertContains(landing, 'id="pageLoader"')
        self.assertContains(landing, 'id="optimisticStatus"')

    def test_robots_links_sitemap_without_disclosing_admin_path(self):
        response = self.client.get(reverse("library:robots_txt"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sitemap: http://testserver/sitemap.xml")
        self.assertContains(response, "Disallow: /staff/")
        self.assertNotContains(response, reverse("admin:index"))

    def test_sitemap_lists_public_pages_and_resources_with_https_urls(self):
        item = self.create_item()

        response = self.client.get(reverse("library:sitemap"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "https://testserver/privacy-and-terms/")
        self.assertContains(
            response,
            f"https://testserver{reverse('library:item_detail', args=(item.pk,))}",
        )
        self.assertNotContains(response, "/staff/")

    def test_public_markup_has_mobile_and_performance_basics(self):
        landing = self.client.get(reverse("library:landing"))

        self.assertContains(
            landing,
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            html=True,
        )
        self.assertNotContains(landing, "fonts.googleapis.com")

        self.client.post(reverse("library:guest_login"))
        dashboard = self.client.get(reverse("library:dashboard"))
        self.assertContains(dashboard, 'id="mobileToggle"')
        self.assertContains(dashboard, 'aria-controls="sidebar"')


class ErrorPageTests(LibraryTestCase):
    def test_missing_page_uses_themed_404(self):
        with self.settings(DEBUG=False):
            response = self.client.get("/this-page-does-not-exist/")

        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "errors/404.html")
        self.assertContains(response, "This page could not be found", status_code=404)

    def test_all_direct_error_handlers_render_without_database_content(self):
        request = RequestFactory().get("/broken/")
        request.user = AnonymousUser()
        cases = (
            (errors.bad_request, 400),
            (errors.permission_denied, 403),
            (errors.page_not_found, 404),
            (errors.server_error, 500),
        )

        for handler, expected_status in cases:
            with self.subTest(status=expected_status):
                response = handler(request)
                self.assertEqual(response.status_code, expected_status)
                self.assertIn(str(expected_status).encode(), response.content)

    def test_csrf_failure_has_actionable_message(self):
        request = RequestFactory().post("/contact/")
        request.user = AnonymousUser()

        response = errors.csrf_failure(request, "test")

        self.assertEqual(response.status_code, 403)
        self.assertIn(b"Refresh the previous page", response.content)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    RATE_LIMIT_ENABLED=True,
    RATE_LIMIT_LOGIN_REQUESTS=2,
    RATE_LIMIT_LOGIN_WINDOW=300,
    RATE_LIMIT_SEARCH_REQUESTS=2,
    RATE_LIMIT_SEARCH_WINDOW=60,
)
class AbuseProtectionTests(LibraryTestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_repeated_login_posts_receive_themed_429(self):
        url = reverse("library:login")
        payload = {
            "email": "unknown@example.com",
            "password": "incorrect",
            "role": "student",
            "privacy_consent": "on",
        }

        self.assertEqual(self.client.post(url, payload).status_code, 200)
        self.assertEqual(self.client.post(url, payload).status_code, 200)
        response = self.client.post(url, payload)

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["Retry-After"], "300")
        self.assertContains(response, "Please slow down", status_code=429)

    def test_failed_login_limits_are_separate_for_accounts_on_the_same_ip(self):
        url = reverse("library:login")

        def payload(email):
            return {
                "email": email,
                "password": "incorrect",
                "role": "student",
                "privacy_consent": "on",
            }

        self.assertEqual(self.client.post(url, payload("one@example.com")).status_code, 200)
        self.assertEqual(self.client.post(url, payload("two@example.com")).status_code, 200)
        self.assertEqual(self.client.post(url, payload("one@example.com")).status_code, 200)
        self.assertEqual(self.client.post(url, payload("two@example.com")).status_code, 200)
        self.assertEqual(self.client.post(url, payload("one@example.com")).status_code, 429)
        self.assertEqual(self.client.post(url, payload("two@example.com")).status_code, 429)

    @override_settings(RATE_LIMIT_LOGIN_REQUESTS=1)
    def test_successful_login_does_not_consume_failed_attempt_allowance(self):
        user = self.create_user(email="reader@example.com")
        EmailAddress.objects.create(
            user=user,
            email=user.email,
            primary=True,
            verified=True,
        )
        url = reverse("library:login")
        successful_payload = {
            "email": user.email,
            "password": "Atlas-Test-Pass-2026!",
            "role": "student",
            "privacy_consent": "on",
        }
        failed_payload = {**successful_payload, "password": "incorrect"}

        self.assertEqual(self.client.post(url, successful_payload).status_code, 302)
        self.client.post(reverse("library:logout"))
        self.assertEqual(self.client.post(url, failed_payload).status_code, 200)
        self.assertEqual(self.client.post(url, failed_payload).status_code, 429)

    def test_repository_browsing_has_no_shared_ip_rate_limit(self):
        url = reverse("library:catalog")

        for _ in range(8):
            self.assertEqual(self.client.get(url).status_code, 200)

    def test_catalog_search_has_a_separate_generous_limit(self):
        url = reverse("library:catalog")

        self.assertEqual(self.client.get(url, {"q": "science"}).status_code, 200)
        self.assertEqual(self.client.get(url, {"q": "history"}).status_code, 200)
        response = self.client.get(url, {"q": "mathematics"})

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["Retry-After"], "60")

    @override_settings(RATE_LIMIT_REGISTER_REQUESTS=1)
    def test_registration_limits_are_separate_for_submitted_accounts(self):
        url = reverse("library:register")

        def payload(email):
            return {
                "full_name": "Test Reader",
                "email": email,
                "role": "student",
                "password1": "Atlas-Test-Pass-2026!",
                "password2": "does-not-match",
                "age_consent": "on",
                "privacy_consent": "on",
            }

        self.assertEqual(self.client.post(url, payload("one@example.com")).status_code, 200)
        self.assertEqual(self.client.post(url, payload("two@example.com")).status_code, 200)
        self.assertEqual(self.client.post(url, payload("one@example.com")).status_code, 429)

    def test_registration_honeypot_rejects_bot_submission(self):
        payload = {
            "full_name": "Spam Bot",
            "email": "spam@example.com",
            "role": "student",
            "password1": "Atlas-Test-Pass-2026!",
            "password2": "Atlas-Test-Pass-2026!",
            "privacy_consent": "on",
            "website": "https://spam.invalid",
        }

        response = self.client.post(reverse("library:register"), payload)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid submission")

    def test_contact_form_rejects_link_spam(self):
        payload = {
            "name": "Link Spammer",
            "email": "spam@example.com",
            "subject": "Links",
            "message": " ".join(
                f"https://spam{index}.invalid" for index in range(4)
            ),
        }

        response = self.client.post(reverse("library:contact"), payload)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please remove excessive links")
        self.assertEqual(ContactMessage.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)


class TransportAndCompressionTests(LibraryTestCase):
    @override_settings(DEBUG=False, SECURE_SSL_REDIRECT=True)
    def test_http_is_redirected_to_https(self):
        response = self.client.get(reverse("library:landing"))

        self.assertEqual(response.status_code, 301)
        self.assertTrue(response["Location"].startswith("https://"))

    def test_large_html_responses_are_gzipped_when_supported(self):
        response = self.client.get(
            reverse("library:privacy_terms"),
            HTTP_ACCEPT_ENCODING="gzip",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Encoding"], "gzip")


class AnalyticsConsentTests(LibraryTestCase):
    def test_server_ignores_usage_events_without_analytics_consent(self):
        user = self.create_user(email="privacy-choice@example.com")
        self.client.force_login(user)

        response = self.client.post(
            reverse("library:usage_heartbeat"),
            {"event": "page_view", "path": "/dashboard/"},
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(WebsiteVisit.objects.filter(user=user).exists())

    def test_server_ignores_usage_events_after_analytics_is_disabled(self):
        user = self.create_user(email="privacy-disabled@example.com")
        self.client.force_login(user)
        self.client.cookies["atlas_cookie_consent"] = "essential"

        response = self.client.post(
            reverse("library:usage_heartbeat"),
            {"event": "page_view", "path": "/dashboard/"},
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(WebsiteVisit.objects.filter(user=user).exists())


class SecurityRegressionTests(LibraryTestCase):
    """Exercise the attack cases included in the technical questionnaire."""

    def test_sql_injection_text_is_treated_as_a_literal_search(self):
        self.create_item(title="Visible research title")

        response = self.client.get(
            reverse("library:catalog"),
            {"q": "' OR 1=1 --"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Visible research title")

    def test_xss_search_payload_is_escaped(self):
        payload = '<script>alert("atlas")</script>'

        response = self.client.get(reverse("library:catalog"), {"q": payload})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, payload)
        self.assertContains(response, "&lt;script&gt;", html=False)

    def test_disguised_pdf_is_rejected_by_library_and_ai_forms(self):
        malicious_library_upload = SimpleUploadedFile(
            "research.pdf",
            b"<script>malicious content</script>",
            content_type="application/pdf",
        )
        malicious_ai_upload = SimpleUploadedFile(
            "analysis.pdf",
            b"<script>malicious content</script>",
            content_type="application/pdf",
        )

        library_form = LibraryItemForm(
            data={
                "collection": "research",
                "call_number": "SEC-001",
                "title": "Security test",
                "author": "ATLAS",
                "details": "A document used to verify upload validation.",
                "publication_month": "2026-09",
                "publication_day": "20",
                "file_type": "PDF",
                "pages": "1",
            },
            files={"resource_abstract": malicious_library_upload},
        )
        ai_form = AIDetectionForm(files={"document": malicious_ai_upload})

        self.assertFalse(library_form.is_valid())
        self.assertIn("not a valid PDF", library_form.errors["resource_abstract"][0])
        self.assertFalse(ai_form.is_valid())
        self.assertIn("not a valid PDF", ai_form.errors["document"][0])

    def test_ai_form_rejects_excessively_long_text(self):
        form = AIDetectionForm(data={"text": "a" * 20001})

        self.assertFalse(form.is_valid())
        self.assertIn("at most 20000", form.errors["text"][0])

    @override_settings(AI_DETECTION_MAX_UPLOAD_MB=25)
    def test_ai_form_accepts_document_larger_than_ten_mb(self):
        upload = SimpleUploadedFile(
            "large-analysis.pdf",
            b"%PDF-" + (b"0" * (11 * 1024 * 1024)),
            content_type="application/pdf",
        )

        form = AIDetectionForm(files={"document": upload})

        self.assertTrue(form.is_valid(), form.errors)

    @override_settings(AI_DETECTION_MAX_UPLOAD_MB=25)
    def test_ai_form_enforces_configured_document_limit(self):
        upload = SimpleUploadedFile(
            "too-large.pdf",
            b"%PDF-" + (b"0" * (25 * 1024 * 1024)),
            content_type="application/pdf",
        )

        form = AIDetectionForm(files={"document": upload})

        self.assertFalse(form.is_valid())
        self.assertIn("25 MB or smaller", form.errors["document"][0])

    def test_forged_session_cookie_does_not_authenticate(self):
        self.client.cookies["sessionid"] = "forged-session-token"

        response = self.client.get(reverse("library:dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("library:login"), response["Location"])

    def test_state_changing_request_without_csrf_token_is_rejected(self):
        user = self.create_user(email="csrf-test@example.com")
        item = self.create_item()
        csrf_client = self.client_class(enforce_csrf_checks=True)
        csrf_client.force_login(user)

        response = csrf_client.post(
            reverse("library:favorite_toggle", args=(item.pk,))
        )

        self.assertEqual(response.status_code, 403)
