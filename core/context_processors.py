from django.conf import settings


def site_meta(request):
    return {
        "SITE_NAME": "LykoonAdds",
        "SUPPORT_EMAIL": "lykoonofficial@gmail.com",
        "MIN_WITHDRAWAL_PKR": settings.MIN_WITHDRAWAL_PKR,
        "WITHDRAWAL_SLA_HOURS": settings.WITHDRAWAL_SLA_HOURS,
        "GOOGLE_ANALYTICS_ID": settings.GOOGLE_ANALYTICS_ID,
    }
