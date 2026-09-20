"""Regression coverage for navigation, metadata, feedback, and mobile UI."""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

from django.conf import settings
from django.test import override_settings
from django.urls import reverse

from library.models import Profile
from library.services import SupportContactPresenter

from .base import LibraryTestCase


class LinkAndFormParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.form_actions = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "a" and "href" in attributes:
            self.links.append(attributes["href"])
        if tag == "form":
            self.form_actions.append(attributes.get("action", ""))


class NavigationAndMetadataTests(LibraryTestCase):
    public_pages = (
        "library:landing",
        "library:login",
        "library:register",
        "library:catalog",
        "library:announcements",
        "library:contact",
        "library:privacy_terms",
    )

    def test_public_pages_have_titles_descriptions_favicon_and_real_links(self):
        for route_name in self.public_pages:
            with self.subTest(route=route_name):
                response = self.client.get(reverse(route_name))
                content = response.content.decode()

                self.assertEqual(response.status_code, 200)
                self.assertIn("| ATLAS</title>", content)
                self.assertIn('<meta\n      name="description"', content)
                self.assertIn("library/images/favicon.svg", content)
                self.assertNotIn('href="#"', content)
                self.assertNotIn('action=""', content)

    def test_footer_links_are_complete_and_clickable(self):
        response = self.client.get(reverse("library:landing"))

        self.assertContains(response, 'class="site-footer"')
        self.assertContains(response, f'href="{reverse("library:landing")}"')
        self.assertContains(response, f'href="{reverse("library:catalog")}"')
        self.assertContains(response, f'href="{reverse("library:contact")}"')
        self.assertContains(response, f'href="mailto:atlastshs@gmail.com"')

    @override_settings(SUPPORT_PHONE="+63 912 345 6789")
    def test_configured_phone_is_clickable_on_contact_page_and_footer(self):
        response = self.client.get(reverse("library:contact"))

        self.assertContains(response, 'href="tel:+639123456789"', count=2)
        self.assertContains(response, "+63 912 345 6789", count=2)

    def test_dashboard_has_accessible_mobile_menu_controls(self):
        self.client.post(reverse("library:guest_login"))

        response = self.client.get(reverse("library:dashboard"))

        self.assertContains(response, 'id="mobileToggle"')
        self.assertContains(response, 'aria-label="Open navigation menu"')
        self.assertContains(response, 'id="mobileMenuClose"')
        self.assertContains(response, 'aria-label="Close navigation menu"')

    def test_reader_dashboard_uses_bookmarks_instead_of_unused_recommendations(self):
        user = self.create_user(role=Profile.Role.STUDENT)
        self.client.force_login(user)

        response = self.client.get(reverse("library:dashboard"))

        self.assertContains(response, "My Bookmarks")
        self.assertNotContains(response, "Recommendations")
        self.assertNotContains(response, "recommended=1")

    def test_rendered_public_internal_links_resolve(self):
        self.create_item()
        self.create_announcement()
        checked = set()

        for route_name in self.public_pages:
            response = self.client.get(reverse(route_name))
            parser = LinkAndFormParser()
            parser.feed(response.content.decode())
            for href in parser.links:
                parsed = urlsplit(href)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                if parsed.path.startswith(("/static/", "/media/")):
                    continue
                target = parsed.path
                if parsed.query:
                    target = f"{target}?{parsed.query}"
                if target in checked:
                    continue
                checked.add(target)
                with self.subTest(source=route_name, target=target):
                    linked_response = self.client.get(target)
                    self.assertLess(linked_response.status_code, 400)


class FormFeedbackTests(LibraryTestCase):
    def test_invalid_contact_form_has_summary_field_errors_and_toast(self):
        response = self.client.post(reverse("library:contact"), {})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="form-alert form-error-summary"')
        self.assertContains(response, "Please correct the following:")
        self.assertContains(response, "Your message was not sent")

    def test_forms_use_instructional_placeholders(self):
        login = self.client.get(reverse("library:login"))
        contact = self.client.get(reverse("library:contact"))

        self.assertContains(login, 'placeholder="Enter your school email address"')
        self.assertContains(login, 'placeholder="Enter your password"')
        self.assertContains(contact, 'placeholder="Briefly describe what you need help with"')
        self.assertContains(contact, "Do not include passwords.")


class AccessibilityAndArchitectureTests(LibraryTestCase):
    def test_reading_preferences_are_available_on_every_page(self):
        response = self.client.get(reverse("library:landing"))

        self.assertContains(response, 'aria-label="Reading preferences"')
        self.assertContains(response, "data-text-size-toggle")
        self.assertContains(response, "data-contrast-toggle")
        self.assertContains(response, 'aria-pressed="false"', count=2)

    def test_accessibility_preferences_use_an_encapsulated_controller(self):
        script = (
            Path(settings.BASE_DIR)
            / "library"
            / "static"
            / "library"
            / "js"
            / "app.js"
        ).read_text(encoding="utf-8")

        self.assertIn("class AccessibilityPreferences", script)
        self.assertIn("atlas_reading_preferences", script)
        self.assertIn("prefers-contrast: more", script)

    def test_support_contact_presenter_normalizes_click_to_call_uri(self):
        context = SupportContactPresenter(
            email="library@example.edu",
            hours="Weekdays",
            phone="+63 (912) 345-6789",
        ).build()

        self.assertEqual(context["support_email"], "library@example.edu")
        self.assertEqual(context["support_hours"], "Weekdays")
        self.assertEqual(context["support_phone"], "+63 (912) 345-6789")
        self.assertEqual(context["support_phone_uri"], "tel:+639123456789")

    def test_primary_text_palette_exceeds_wcag_aa_contrast(self):
        def luminance(hex_color):
            channels = (
                int(hex_color[index : index + 2], 16) / 255
                for index in (0, 2, 4)
            )
            red, green, blue = (
                value / 12.92
                if value <= 0.03928
                else ((value + 0.055) / 1.055) ** 2.4
                for value in channels
            )
            return 0.2126 * red + 0.7152 * green + 0.0722 * blue

        def contrast(foreground, background):
            lighter, darker = sorted(
                (luminance(foreground), luminance(background)), reverse=True
            )
            return (lighter + 0.05) / (darker + 0.05)

        for foreground, background in (
            ("282326", "ffffff"),
            ("5f5754", "ffffff"),
            ("4a111c", "ffffff"),
            ("ffffff", "4a111c"),
            ("625956", "ffffff"),
        ):
            with self.subTest(foreground=foreground, background=background):
                self.assertGreaterEqual(contrast(foreground, background), 4.5)
