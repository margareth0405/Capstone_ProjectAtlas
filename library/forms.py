from django import forms
from django.contrib.auth import authenticate, get_user_model, password_validation
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Announcement, ContactMessage, LibraryItem, Profile


User = get_user_model()


class StyledFormMixin:
    """Small presentation helper; validation remains entirely server-side."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()

    def _style_fields(self):
        for field in self.fields.values():
            css_class = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs["class"] = " ".join(
                value for value in (field.widget.attrs.get("class"), css_class) if value
            )


class BaseAccountCreationForm(StyledFormMixin, UserCreationForm):
    """Shared account validation and persistence for reader account forms."""

    full_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    role = forms.ChoiceField(choices=Profile.Role.choices)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("full_name", "email", "role", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def _profile_defaults(self):
        return {"role": self.cleaned_data["role"]}

    def save(self, commit=True):
        user = super().save(commit=False)
        email = self.cleaned_data["email"]
        full_name = " ".join(self.cleaned_data["full_name"].split())
        user.first_name, _, user.last_name = full_name.partition(" ")
        user.username = email
        user.email = email
        if commit:
            user.save()
            Profile.objects.update_or_create(
                user=user,
                defaults=self._profile_defaults(),
            )
        return user


class RegistrationForm(BaseAccountCreationForm):
    privacy_consent = forms.BooleanField(
        required=True,
        label="I agree to the privacy and confidentiality statement.",
    )

    def __init__(self, *args, privacy_consent_version="", **kwargs):
        self.privacy_consent_version = privacy_consent_version
        super().__init__(*args, **kwargs)

    def _profile_defaults(self):
        defaults = super()._profile_defaults()
        defaults.update(
            {
                "privacy_consent_accepted_at": timezone.now(),
                "privacy_consent_version": self.privacy_consent_version,
            }
        )
        return defaults


class RoleLoginForm(StyledFormMixin, forms.Form):
    email = forms.EmailField()
    password = forms.CharField(strip=False, widget=forms.PasswordInput)
    role = forms.ChoiceField(choices=Profile.Role.choices)
    privacy_consent = forms.BooleanField(required=True)

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned
        email = cleaned.get("email", "").strip().lower()
        password = cleaned.get("password")
        user = User.objects.filter(email__iexact=email).first()
        username = user.get_username() if user else email
        self.user_cache = authenticate(self.request, username=username, password=password)
        if self.user_cache is None:
            raise ValidationError("Invalid email or password.")
        if not self.user_cache.is_active:
            raise ValidationError("This account is inactive.")
        if self.user_cache.is_staff or self.user_cache.is_superuser:
            raise ValidationError("Use the administrator sign-in for this account.")
        profile = getattr(self.user_cache, "profile", None)
        if not profile or profile.role != cleaned.get("role"):
            raise ValidationError("This account does not match the selected role.")
        return cleaned

    def get_user(self):
        return self.user_cache


class LibraryItemForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = LibraryItem
        fields = (
            "collection",
            "call_number",
            "title",
            "author",
            "details",
            "file_type",
            "file_size",
            "pages",
            "resource",
            "external_url",
        )
        widgets = {"details": forms.Textarea(attrs={"rows": 4})}

class AnnouncementForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Announcement
        fields = (
            "title",
            "body",
            "category",
            "is_featured",
            "is_published",
            "published_at",
        )
        widgets = {
            "body": forms.Textarea(attrs={"rows": 6}),
            "published_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

class AdminCreatedUserForm(BaseAccountCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].help_text = password_validation.password_validators_help_text_html()


class ContactForm(StyledFormMixin, forms.ModelForm):
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = ContactMessage
        fields = ("name", "email", "subject", "message")
        widgets = {"message": forms.Textarea(attrs={"rows": 6})}

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise ValidationError("Invalid submission.")
        return ""
