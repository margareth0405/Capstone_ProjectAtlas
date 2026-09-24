
import os
import django

# Load your Django project's configuration
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "atlas.settings")

django.setup()

from django.conf import settings
from django.core.mail import send_mail

print("Checking ATLAS email configuration...")

print("Email backend:", settings.EMAIL_BACKEND)
print("Email host:", settings.EMAIL_HOST)
print("Email port:", settings.EMAIL_PORT)
print("TLS enabled:", settings.EMAIL_USE_TLS)
print("Email sender:", settings.EMAIL_HOST_USER)
print("App Password configured:", bool(settings.EMAIL_HOST_PASSWORD))

print("Attempting to send a test email...")

try:
    result = send_mail(
        subject="ATLAS Gmail SMTP Test",
        message="This is a test email from the ATLAS system.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=["libralinksystem@gmail.com"],
        fail_silently=False,
    )

    print("Email send result:", result)

except Exception as error:
    print("Email test failed.")
    print("Error type:", type(error).__name__)
    print("Error message:", str(error))