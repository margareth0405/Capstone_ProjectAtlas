"""Model and authentication-storage contracts."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction

from library.models import Favorite, Profile

from .base import LibraryTestCase, TEST_PASSWORD


class AuthenticationModelTests(LibraryTestCase):
    def test_project_uses_djangos_builtin_user_model(self):
        self.assertEqual(settings.AUTH_USER_MODEL, "auth.User")
        self.assertIs(get_user_model(), User)

    def test_create_user_hashes_password(self):
        user = self.create_user()

        self.assertNotEqual(user.password, TEST_PASSWORD)
        self.assertTrue(user.check_password(TEST_PASSWORD))

    def test_new_nonstaff_user_gets_separate_default_profile(self):
        user = get_user_model().objects.create_user(
            username="new-profile@example.com",
            email="new-profile@example.com",
            password=TEST_PASSWORD,
        )

        profile = Profile.objects.get(user=user)
        self.assertEqual(user.profile.pk, profile.pk)
        self.assertEqual(profile.role, Profile.Role.STUDENT)
        self.assertIsNone(profile.privacy_consent_accepted_at)
        self.assertEqual(profile.privacy_consent_version, "")


class FavoriteModelTests(LibraryTestCase):
    def test_a_user_cannot_favorite_the_same_item_twice(self):
        user = self.create_user()
        item = self.create_item()
        Favorite.objects.create(user=user, item=item)

        with self.assertRaises(IntegrityError), transaction.atomic():
            Favorite.objects.create(user=user, item=item)

        self.assertEqual(Favorite.objects.filter(user=user, item=item).count(), 1)
