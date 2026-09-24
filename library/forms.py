import re
from datetime import date
from io import BytesIO
from pathlib import Path

from django import forms
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, password_validation
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image, ImageOps, UnidentifiedImageError

from .models import Announcement, ContactMessage, LibraryItem, Profile
from .services.accounts import AccountEmailPolicy
from .services.uploads import DocumentUploadPolicy, DocumentUploadValidationError

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

    full_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={"placeholder": "Example: Juan Dela Cruz", "autocomplete": "name"}
        ),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Example: name@deped.gov.ph or student@example.com",
                "autocomplete": "email",
            }
        )
    )
    role = forms.ChoiceField(choices=Profile.Role.choices)
    email_policy_class = AccountEmailPolicy

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("full_name", "email", "role", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update({"minlength": "6"})
        self.fields["password2"].widget.attrs.update({"minlength": "6"})

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get("email", "")
        role = cleaned.get("role", "")
        error = self.email_policy_class().error_for(email=email, role=role)
        if error:
            self.add_error("email", error)
        return cleaned

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
    website = forms.CharField(required=False, widget=forms.HiddenInput)
    age_consent = forms.BooleanField(
        required=True,
        label=(
            "I confirm that I am legally able to consent, or that my parent "
            "or legal guardian has authorized this account and reviewed the "
            "privacy notice."
        ),
    )
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
                "age_consent_confirmed_at": timezone.now(),
                "age_consent_version": self.privacy_consent_version,
            }
        )
        return defaults

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise ValidationError("Invalid submission.")
        return ""


class RoleLoginForm(StyledFormMixin, forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Example: student@example.com",
                "autocomplete": "email",
            }
        )
    )
    password = forms.CharField(
        strip=False,
        min_length=6,
        error_messages={
            "min_length": "Your password must be at least 6 characters long.",
        },
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
                "minlength": "6",
            }
        ),
    )
    role = forms.ChoiceField(choices=Profile.Role.choices)
    privacy_consent = forms.BooleanField(required=True)
    email_policy_class = AccountEmailPolicy

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
        email_error = self.email_policy_class().error_for(
            email=email,
            role=cleaned.get("role", ""),
        )
        if email_error:
            self.add_error("email", email_error)
            return cleaned
        self.user_cache = authenticate(self.request, email=email, password=password)
        if self.user_cache is None:
            raise ValidationError(
                "Incorrect email or password. Check your details and try again."
            )
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

    maximum_cover_size = 5 * 1024 * 1024
    maximum_document_size = 10 * 1024 * 1024
    maximum_cover_pixels = 20_000_000
    maximum_cover_dimensions = (1200, 1800)
    supported_cover_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    supported_document_extensions = {".pdf", ".docx"}
    document_upload_policy_class = DocumentUploadPolicy

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
            "cover_image",
            "resource_abstract",
            "file_type",
            "pages",
        )
        widgets = {
            "call_number": forms.TextInput(
                attrs={"placeholder": "Example: QA76.73-T001"}
            ),
            "title": forms.TextInput(
                attrs={"placeholder": "Enter the complete resource title"}
            ),
            "author": forms.TextInput(
                attrs={"placeholder": "Enter the author or organization"}
            ),
            "details": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": "Summarize what readers will learn from this resource.",
                }
            ),
            "pages": forms.NumberInput(
                attrs={"placeholder": "Example: 120", "min": "0", "inputmode": "numeric"}
            ),
            "file_type": forms.RadioSelect,
            "cover_image": forms.ClearableFileInput(
                attrs={"accept": "image/jpeg,image/png,image/webp"}
            ),
            "resource_abstract": forms.ClearableFileInput(
                attrs={
                    "accept": ".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                }
            ),
        }
        labels = {
            "cover_image": "Cover (optional)",
            "resource_abstract": "Resource abstract",
            "file_type": "Resource abstract format",
        }
        help_texts = {
            "details": "Add a concise description or abstract for readers.",
            "cover_image": "Upload an optional JPG, PNG, or WebP cover image up to 5 MB.",
            "resource_abstract": "Upload the required PDF or Word (.docx) resource abstract, up to 10 MB.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["file_type"].widget.attrs["class"] = "resource-format-toggle"
        self.fields["publication_day"].widget.attrs.update(
            {"placeholder": "Example: 15", "inputmode": "numeric"}
        )
        self.fields["resource_abstract"].required = not bool(
            self.instance.pk and self.instance.resource_abstract
        )
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

        upload = cleaned.get("resource_abstract") or self.instance.resource_abstract
        file_type = cleaned.get("file_type")
        if upload:
            extension = Path(upload.name).suffix.lower()
            allowed = {
                LibraryItem.FileType.PDF: {".pdf"},
                LibraryItem.FileType.WORD: {".docx"},
            }
            if extension not in allowed.get(file_type, set()):
                self.add_error(
                    "resource_abstract",
                    "The Resource abstract must match the selected PDF or Word format.",
                )
        return cleaned

    def clean_cover_image(self):
        cover = self.cleaned_data.get("cover_image")
        if not cover:
            return cover
        if Path(cover.name).suffix.lower() not in self.supported_cover_extensions:
            raise ValidationError("Upload a JPG, PNG, or WebP cover image.")
        if cover.size > self.maximum_cover_size:
            raise ValidationError("The cover image must be 5 MB or smaller.")
        try:
            cover.seek(0)
            with Image.open(cover) as source:
                if source.width * source.height > self.maximum_cover_pixels:
                    raise ValidationError(
                        "The cover image dimensions are too large."
                    )
                image = ImageOps.exif_transpose(source)
                image.thumbnail(self.maximum_cover_dimensions, Image.Resampling.LANCZOS)
                if image.mode not in {"RGB", "RGBA"}:
                    image = image.convert("RGBA" if "transparency" in image.info else "RGB")
                output = BytesIO()
                image.save(output, format="WEBP", quality=82, method=6)
        except ValidationError:
            raise
        except (
            Image.DecompressionBombError,
            OSError,
            UnidentifiedImageError,
            ValueError,
        ) as exc:
            raise ValidationError("Upload a valid JPG, PNG, or WebP cover image.") from exc
        optimized = ContentFile(
            output.getvalue(),
            name=f"{Path(cover.name).stem}.webp",
        )
        optimized.content_type = "image/webp"
        return optimized

    def clean_resource_abstract(self):
        resource_abstract = self.cleaned_data.get("resource_abstract")
        if resource_abstract is False:
            raise ValidationError("Resource abstract cannot be removed without a replacement.")
        if not resource_abstract:
            return resource_abstract
        if Path(resource_abstract.name).suffix.lower() not in self.supported_document_extensions:
            raise ValidationError("Upload a PDF or Word (.docx) Resource abstract.")
        if resource_abstract.size > self.maximum_document_size:
            raise ValidationError("The Resource abstract must be 10 MB or smaller.")
        try:
            self.document_upload_policy_class().validate(resource_abstract)
        except DocumentUploadValidationError as exc:
            raise ValidationError(str(exc)) from exc
        return resource_abstract

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.published_on = self.cleaned_data.get("resolved_publication_date")
        instance.publication_day_known = bool(self.cleaned_data.get("publication_day"))
        if commit:
            instance.save()
            self.save_m2m()
        return instance

class AnnouncementForm(StyledFormMixin, forms.ModelForm):
    """Edit announcement content; publication is a separate staff action."""

    class Meta:
        model = Announcement
        fields = (
            "title",
            "body",
            "category",
        )
        widgets = {
            "title": forms.TextInput(
                attrs={"placeholder": "Enter a short, specific announcement title"}
            ),
            "body": forms.Textarea(
                attrs={
                    "rows": 6,
                    "placeholder": "Write the complete update readers need to know.",
                }
            ),
        }


class AdminCreatedUserForm(BaseAccountCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].help_text = password_validation.password_validators_help_text_html()


class AIDetectionForm(StyledFormMixin, forms.Form):
    """Accept one bounded text sample or supported in-memory document upload."""

    supported_extensions = (".pdf", ".docx")
    document_upload_policy_class = DocumentUploadPolicy

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
        help_text="Accepted formats: PDF and Word (.docx).",
        widget=forms.ClearableFileInput(
            attrs={"accept": ".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maximum_upload_mb = settings.AI_DETECTION_MAX_UPLOAD_MB
        self.maximum_upload_size = self.maximum_upload_mb * 1024 * 1024
        self.fields["document"].help_text = (
            "Accepted formats: PDF and Word (.docx), up to "
            f"{self.maximum_upload_mb} MB."
        )

    def clean_document(self):
        document = self.cleaned_data.get("document")
        if not document:
            return document
        filename = document.name.lower()
        if not filename.endswith(self.supported_extensions):
            raise ValidationError("Upload a PDF or Word (.docx) document.")
        if document.size > self.maximum_upload_size:
            raise ValidationError(
                f"The document must be {self.maximum_upload_mb} MB or smaller."
            )
        try:
            self.document_upload_policy_class().validate(document)
        except DocumentUploadValidationError as exc:
            raise ValidationError(str(exc)) from exc
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
    privacy_consent = forms.BooleanField(
        required=True,
        label=(
            "I agree that ATLAS may use the information in this form to "
            "review and respond to my request."
        ),
    )

    class Meta:
        model = ContactMessage
        fields = ("name", "email", "request_type", "subject", "message")
        widgets = {
            "name": forms.TextInput(
                attrs={"placeholder": "Example: Maria Santos", "autocomplete": "name"}
            ),
            "email": forms.EmailInput(
                attrs={
                    "placeholder": "Example: maria.santos@example.com",
                    "autocomplete": "email",
                }
            ),
            "subject": forms.TextInput(
                attrs={"placeholder": "Example: Help opening a resource"}
            ),
            "message": forms.Textarea(
                attrs={
                    "rows": 6,
                }
            ),
        }

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise ValidationError("Invalid submission.")
        return ""

    def save(self, commit=True):
        message = super().save(commit=False)
        message.privacy_consent_accepted_at = timezone.now()
        if commit:
            message.save()
        return message

    def clean_message(self):
        message = self.cleaned_data["message"].strip()
        if len(re.findall(r"(?:https?://|www\.)", message, flags=re.IGNORECASE)) > 3:
            raise ValidationError("Please remove excessive links and try again.")
        return message
