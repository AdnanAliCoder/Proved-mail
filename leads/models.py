import uuid
from django.conf import settings
from django.db import models
from django.utils.text import slugify


class SiteSettings(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    site_name = models.CharField(max_length=80, default="ProveMails")
    tagline = models.CharField(max_length=180, default="Verify emails. Clean leads. Work smarter.")
    site_url = models.URLField(default="http://127.0.0.1:8000")
    homepage_title = models.CharField(max_length=180, default="ProveMails — Bulk Email Verification")
    meta_description = models.CharField(max_length=320, default="Verify email leads, classify risky addresses, and export clean CSV or Excel results.")
    adsense_code = models.TextField(blank=True, help_text="Optional AdSense script/snippet. Only the site administrator can edit this.")
    analytics_code = models.TextField(blank=True, help_text="Optional Google Analytics tag/snippet.")
    extra_head_code = models.TextField(blank=True, help_text="Optional site-wide verification or analytics snippets.")
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.site_name


class SitePage(models.Model):
    slug = models.SlugField(max_length=80, unique=True)
    title = models.CharField(max_length=140)
    seo_title = models.CharField(max_length=180, blank=True)
    meta_description = models.CharField(max_length=320, blank=True)
    body_text = models.TextField(blank=True, help_text="Plain text is supported; line breaks are displayed on the public page.")
    is_published = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class SearchConsoleVerification(models.Model):
    filename = models.CharField(max_length=120, unique=True)
    file_content = models.TextField()
    uploaded_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.filename


class EmailJob(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        CANCELED = "canceled", "Canceled"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="email_jobs")
    source_file = models.FileField(upload_to="lead_uploads/%Y/%m/")
    source_filename = models.CharField(max_length=255)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED, db_index=True)
    email_field = models.CharField(max_length=120, blank=True)
    total = models.PositiveIntegerField(default=0)
    completed = models.PositiveIntegerField(default=0)
    phase = models.CharField(max_length=24, default="queued")
    retry_count = models.PositiveIntegerField(default=0)
    valid_count = models.PositiveIntegerField(default=0)
    invalid_count = models.PositiveIntegerField(default=0)
    risky_count = models.PositiveIntegerField(default=0)
    unknown_count = models.PositiveIntegerField(default=0)
    last_log = models.CharField(max_length=320, blank=True)
    smtp_available = models.BooleanField(null=True, blank=True)
    cancel_requested = models.BooleanField(default=False)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["owner", "-created_at"]), models.Index(fields=["status", "created_at"])]

    @property
    def progress_percent(self):
        if self.status == self.Status.COMPLETED:
            return 100
        if not self.total:
            return 0
        return min(100, int((self.completed / self.total) * 100))

    @property
    def classified_count(self):
        return self.valid_count + self.invalid_count + self.risky_count + self.unknown_count

    def __str__(self):
        return f"{self.source_filename} ({self.status})"


class VerificationRow(models.Model):
    job = models.ForeignKey(EmailJob, on_delete=models.CASCADE, related_name="results")
    position = models.PositiveIntegerField()
    source_row = models.JSONField(default=dict)
    verified_email = models.EmailField(max_length=320, blank=True)
    status = models.CharField(max_length=12, blank=True, db_index=True)
    reason = models.CharField(max_length=80, blank=True)
    confidence = models.PositiveSmallIntegerField(default=0)
    detail = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["position"]
        constraints = [models.UniqueConstraint(fields=["job", "position"], name="unique_job_result_position")]
        indexes = [models.Index(fields=["job", "status"])]

    def __str__(self):
        return f"{self.verified_email} · {self.status}"
