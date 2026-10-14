from django.contrib import admin
from django.urls import include, path, re_path
from django.conf import settings
from django.conf.urls.static import static
from leads import views

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("admin-signup/", views.bootstrap_admin, name="bootstrap_admin"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("jobs/create/", views.create_job, name="create_job"),
    path("jobs/<uuid:job_id>/", views.job_detail, name="job_detail"),
    path("jobs/<uuid:job_id>/status/", views.job_status, name="job_status"),
    path("jobs/<uuid:job_id>/cancel/", views.cancel_job, name="cancel_job"),
    path("jobs/<uuid:job_id>/download/", views.download_results, name="download_results"),
    path("control/", views.control_dashboard, name="control_dashboard"),
    path("control/settings/", views.control_settings, name="control_settings"),
    path("control/pages/", views.control_pages, name="control_pages"),
    path("control/pages/<slug:slug>/", views.edit_page, name="edit_page"),
    path("pages/<slug:slug>/", views.public_page, name="public_page"),
    path("robots.txt", views.robots_txt, name="robots_txt"),
    path("sitemap.xml", views.sitemap_xml, name="sitemap_xml"),
    re_path(r"^(?P<filename>google[A-Za-z0-9_-]+\\.html)$", views.search_console_verification, name="search_console_verification"),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
