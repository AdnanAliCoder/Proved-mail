from django.contrib import admin
from .models import EmailJob, SearchConsoleVerification, SitePage, SiteSettings, VerificationRow

@admin.register(EmailJob)
class EmailJobAdmin(admin.ModelAdmin):
    list_display = ("source_filename", "owner", "status", "total", "completed", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("source_filename", "owner__email")
    readonly_fields = ("id", "created_at", "updated_at", "started_at", "finished_at")

@admin.register(VerificationRow)
class VerificationRowAdmin(admin.ModelAdmin):
    list_display = ("job", "position", "verified_email", "status", "confidence")
    list_filter = ("status",)
    search_fields = ("verified_email",)

@admin.register(SitePage)
class SitePageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_published", "updated_at")
    list_filter = ("is_published",)
    prepopulated_fields = {"slug": ("title",)}

admin.site.register(SiteSettings)
admin.site.register(SearchConsoleVerification)
