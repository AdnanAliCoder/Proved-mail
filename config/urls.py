from django.contrib import admin
from django.urls import include, path, re_path
from django.conf import settings
from django.conf.urls.static import static
from leads import views

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("", include("leads.urls")),
    re_path(r"^(?P<filename>google[A-Za-z0-9_-]+\.html)$", views.search_console_verification, name="search_console_verification"),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
