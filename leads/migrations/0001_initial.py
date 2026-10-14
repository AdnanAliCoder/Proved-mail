import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_public_content(apps, schema_editor):
    SiteSettings = apps.get_model("leads", "SiteSettings")
    SitePage = apps.get_model("leads", "SitePage")
    SiteSettings.objects.get_or_create(
        id=1,
        defaults={
            "site_name": "ProveMails",
            "tagline": "Verify emails. Clean leads. Work smarter.",
            "site_url": "http://127.0.0.1:8000",
            "homepage_title": "ProveMails — Bulk Email Verification",
            "meta_description": "Verify email leads, classify risky addresses, and export clean CSV or Excel results.",
        },
    )
    pages = [
        ("about", "About ProveMails", "About ProveMails | Email verification", "What ProveMails does and how it handles verification results.", "ProveMails helps organize email lead lists with syntax, domain, DNS and supported SMTP verification signals.\n\nResults are grouped into valid, invalid, risky and unknown categories. These labels describe the available signals; they are not a guarantee that an email will be delivered.\n\nUse the administrator panel to update this page and its search metadata."),
        ("privacy-policy", "Privacy Policy", "Privacy Policy | ProveMails", "How uploaded lead files and verification results are used.", "ProveMails processes files uploaded by the authorized administrator. Uploaded source files and results are stored so a batch can be reviewed and exported later.\n\nOnly upload lead data you are authorized to process. Restrict access to the server and its database, keep credentials private, and remove old jobs when they are no longer needed.\n\nMailbox verification may involve DNS requests and SMTP connection attempts to recipient mail servers. SMTP results can be limited by providers or network restrictions.\n\nThis starter policy is a template and should be reviewed for your deployment and legal requirements."),
        ("terms", "Terms of Use", "Terms of Use | ProveMails", "Responsible use and verification limitations.", "Use ProveMails only with email data you are permitted to process. Do not use it to spam, harass, evade provider protections or violate applicable laws or service terms.\n\nVerification results are best-effort indicators. Mail providers can block, defer or obscure mailbox checks, so a valid result is not a guarantee of delivery and an unknown result is not proof of invalidity.\n\nYou are responsible for securing your deployment, protecting uploaded lead files and validating results before making outreach decisions."),
        ("contact", "Contact", "Contact ProveMails", "How to contact the ProveMails administrator.", "For questions about this installation, contact the ProveMails site administrator using the contact details configured for your deployment.\n\nThe administrator can edit this page from the ProveMails admin panel."),
    ]
    for slug, title, seo_title, description, body in pages:
        SitePage.objects.get_or_create(
            slug=slug,
            defaults={"title": title, "seo_title": seo_title, "meta_description": description, "body_text": body, "is_published": True},
        )


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="SearchConsoleVerification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("filename", models.CharField(max_length=120, unique=True)),
                ("file_content", models.TextField()),
                ("uploaded_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="SitePage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=80, unique=True)),
                ("title", models.CharField(max_length=140)),
                ("seo_title", models.CharField(blank=True, max_length=180)),
                ("meta_description", models.CharField(blank=True, max_length=320)),
                ("body_text", models.TextField(blank=True, help_text="Plain text is supported; line breaks are displayed on the public page.")),
                ("is_published", models.BooleanField(default=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["title"]},
        ),
        migrations.CreateModel(
            name="SiteSettings",
            fields=[
                ("id", models.PositiveSmallIntegerField(default=1, editable=False, primary_key=True, serialize=False)),
                ("site_name", models.CharField(default="ProveMails", max_length=80)),
                ("tagline", models.CharField(default="Verify emails. Clean leads. Work smarter.", max_length=180)),
                ("site_url", models.URLField(default="http://127.0.0.1:8000")),
                ("homepage_title", models.CharField(default="ProveMails — Bulk Email Verification", max_length=180)),
                ("meta_description", models.CharField(default="Verify email leads, classify risky addresses, and export clean CSV or Excel results.", max_length=320)),
                ("adsense_code", models.TextField(blank=True, help_text="Optional AdSense script/snippet. Only the site administrator can edit this.")),
                ("analytics_code", models.TextField(blank=True, help_text="Optional Google Analytics tag/snippet.")),
                ("extra_head_code", models.TextField(blank=True, help_text="Optional site-wide verification or analytics snippets.")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="EmailJob",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("source_file", models.FileField(upload_to="lead_uploads/%Y/%m/")),
                ("source_filename", models.CharField(max_length=255)),
                ("status", models.CharField(choices=[("queued", "Queued"), ("running", "Running"), ("completed", "Completed"), ("canceled", "Canceled"), ("failed", "Failed")], db_index=True, default="queued", max_length=16)),
                ("email_field", models.CharField(blank=True, max_length=120)),
                ("total", models.PositiveIntegerField(default=0)),
                ("completed", models.PositiveIntegerField(default=0)),
                ("phase", models.CharField(default="queued", max_length=24)),
                ("retry_count", models.PositiveIntegerField(default=0)),
                ("valid_count", models.PositiveIntegerField(default=0)),
                ("invalid_count", models.PositiveIntegerField(default=0)),
                ("risky_count", models.PositiveIntegerField(default=0)),
                ("unknown_count", models.PositiveIntegerField(default=0)),
                ("last_log", models.CharField(blank=True, max_length=320)),
                ("smtp_available", models.BooleanField(blank=True, null=True)),
                ("cancel_requested", models.BooleanField(default=False)),
                ("error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="email_jobs", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["owner", "-created_at"], name="leads_job_owner_created"),
                    models.Index(fields=["status", "created_at"], name="leads_job_status_created"),
                ],
            },
        ),
        migrations.CreateModel(
            name="VerificationRow",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("position", models.PositiveIntegerField()),
                ("source_row", models.JSONField(default=dict)),
                ("verified_email", models.EmailField(blank=True, max_length=320)),
                ("status", models.CharField(blank=True, db_index=True, max_length=12)),
                ("reason", models.CharField(blank=True, max_length=80)),
                ("confidence", models.PositiveSmallIntegerField(default=0)),
                ("detail", models.JSONField(blank=True, default=dict)),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="results", to="leads.emailjob")),
            ],
            options={
                "ordering": ["position"],
                "indexes": [models.Index(fields=["job", "status"], name="leads_result_job_status")],
                "constraints": [models.UniqueConstraint(fields=("job", "position"), name="unique_job_result_position")],
            },
        ),
        migrations.RunPython(seed_public_content, migrations.RunPython.noop),
    ]
