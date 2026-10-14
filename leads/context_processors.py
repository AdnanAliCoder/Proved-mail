from django.conf import settings
from .models import SiteSettings

_LOCAL_DEFAULT_URL = "http://127.0.0.1:8000"

def site_context(request):
    try:
        site_settings = SiteSettings.objects.filter(pk=1).first()
        if site_settings and site_settings.site_url == _LOCAL_DEFAULT_URL and settings.SITE_URL != _LOCAL_DEFAULT_URL:
            site_settings.site_url = settings.SITE_URL
            site_settings.save(update_fields=["site_url", "updated_at"])
        effective_url = site_settings.site_url if site_settings else settings.SITE_URL
    except Exception:
        site_settings = None
        effective_url = settings.SITE_URL
    return {"site_settings": site_settings, "site_url": (effective_url or settings.SITE_URL).rstrip("/")}
