from django.urls import path
from . import views

urlpatterns = [
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
]
