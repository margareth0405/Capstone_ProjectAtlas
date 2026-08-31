from datetime import date
from pathlib import Path
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
        self.user_cache = authenticate(self.request, email=email, password=password)
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
    """Validate uploaded PDF/Word resources and publication precision."""

    publication_month = forms.RegexField(
        regex=r"^\d{4}-(0[1-9]|1[0-2])$",
        label="Publication month and year",
        help_text="Select the publication month and year.",
        widget=forms.TextInput(attrs={"type": "month"}),
    )
    publication_day = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=31,
        label="Publication day (optional)",
        help_text="Leave blank when only the month and year are known.",
    )

    class Meta:
        model = LibraryItem
        fields = (
            "collection",
            "call_number",
            "title",
            "author",
            "details",
            "file_type",
            "pages",
            "resource",
        )
        widgets = {
            "details": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": "Description or abstract can be entered here.",
                }
            ),
            "file_type": forms.RadioSelect,
        }
        help_texts = {
            "details": "Add a concise description or abstract for readers.",
            "resource": "Upload one PDF, .doc, or .docx file.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["file_type"].widget.attrs["class"] = "resource-format-toggle"
        self.fields["resource"].required = not bool(self.instance.pk and self.instance.resource)
        if self.instance.pk and self.instance.published_on and not self.is_bound:
            self.fields["publication_month"].initial = self.instance.published_on.strftime("%Y-%m")
            if self.instance.publication_day_known:
                self.fields["publication_day"].initial = self.instance.published_on.day

    def clean(self):
        cleaned = super().clean()
        month_value = cleaned.get("publication_month")
        day_value = cleaned.get("publication_day")
        if month_value:
            year, month = (int(part) for part in month_value.split("-"))
            try:
                cleaned["resolved_publication_date"] = date(year, month, day_value or 1)
            except ValueError:
                self.add_error("publication_day", "Enter a valid day for the selected month.")

        uploaded_replacement = cleaned.get("resource")
        if uploaded_replacement and self.instance.external_url:
            self.instance.external_url = ""
        upload = uploaded_replacement or self.instance.resource
        file_type = cleaned.get("file_type")
        if upload:
            extension = Path(upload.name).suffix.lower()
            allowed = {
                LibraryItem.FileType.PDF: {".pdf"},
                LibraryItem.FileType.WORD: {".doc", ".docx"},
            }
            if extension not in allowed.get(file_type, set()):
                self.add_error(
                    "resource",
                    "The uploaded file must match the selected PDF or Word format.",
                )
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.published_on = self.cleaned_data.get("resolved_publication_date")
        instance.publication_day_known = bool(self.cleaned_data.get("publication_day"))
        if commit:
            instance.save()
            self.save_m2m()
        return instance

class AnnouncementForm(StyledFormMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk and not self.is_bound:
            self.fields["is_published"].initial = True

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


class AIDetectionForm(StyledFormMixin, forms.Form):
    """Accept one bounded text sample or supported in-memory document upload."""

    maximum_upload_size = 10 * 1024 * 1024
    supported_extensions = (".pdf", ".docx")

    text = forms.CharField(
        required=False,
        min_length=100,
        max_length=20000,
        label="Paste text",
        help_text="Use 100 to 20,000 characters.",
        widget=forms.Textarea(
            attrs={
                "rows": 14,
                "placeholder": "Paste an essay, report, or other writing here...",
            }
        ),
    )
    document = forms.FileField(
        required=False,
        label="Upload a document",
        help_text="Accepted formats: PDF and Word (.docx), up to 10 MB.",
        widget=forms.ClearableFileInput(
            attrs={"accept": ".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
        ),
    )

    def clean_document(self):
        document = self.cleaned_data.get("document")
        if not document:
            return document
        filename = document.name.lower()
        if not filename.endswith(self.supported_extensions):
            raise ValidationError("Upload a PDF or Word (.docx) document.")
        if document.size > self.maximum_upload_size:
            raise ValidationError("The document must be 10 MB or smaller.")
        return document

    def clean(self):
        cleaned = super().clean()
        text = cleaned.get("text")
        document = cleaned.get("document")
        if not text and not document:
            raise ValidationError("Paste text or upload a PDF or Word document.")
        if text and document:
            raise ValidationError("Use either pasted text or one document, not both.")
        return cleaned


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
