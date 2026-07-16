import logging

import requests
from django.conf import settings
from django.core.mail import send_mail as django_send_mail

logger = logging.getLogger(__name__)


def send_otp_email(to_email, subject, message):
    """
    Sends an email via Brevo's HTTPS API if BREVO_API_KEY is configured
    (works on hosts that block outbound SMTP, since it's a normal HTTPS
    request). Falls back to Django's regular SMTP email backend otherwise.
    Never raises — logs and returns False on failure so registration/OTP
    flows always complete for the user even if the email couldn't be sent.
    """
    api_key = getattr(settings, "BREVO_API_KEY", "")
    sender_email = getattr(settings, "BREVO_SENDER_EMAIL", "") or settings.DEFAULT_FROM_EMAIL

    if api_key:
        try:
            response = requests.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={
                    "api-key": api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json={
                    "sender": {"name": "LykoonAdds", "email": sender_email},
                    "to": [{"email": to_email}],
                    "subject": subject,
                    "textContent": message,
                },
                timeout=10,
            )
            if response.status_code >= 300:
                logger.warning("Brevo email failed (%s): %s", response.status_code, response.text)
                return False
            return True
        except Exception as exc:  # noqa: BLE001 - never let email break the request
            logger.warning("Brevo email error: %s", exc)
            return False

    # No Brevo key configured — fall back to plain SMTP (console in dev).
    try:
        django_send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=True,
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("SMTP email error: %s", exc)
        return False
