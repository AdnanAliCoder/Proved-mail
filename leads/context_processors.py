from .models import SiteSettings

def site_context(request):
    try:
        site_settings = SiteSettings.objects.filter(pk=1).first()
    except Exception:
        site_settings = None
    return {"site_settings": site_settings}
