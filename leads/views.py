import csv
import io
import re
from pathlib import Path
from functools import wraps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape
from django.utils.text import slugify
from django.views.decorators.http import require_POST
from .forms import AdminBootstrapForm, SearchConsoleFileForm, SitePageForm, SiteSettingsForm
from .models import EmailJob, SearchConsoleVerification, SitePage, SiteSettings
from .services import read_lead_file

STARTER_PAGES = [
    ("about", "About ProveMails", "What ProveMails does and how it handles verification results."),
    ("privacy-policy", "Privacy Policy", "How uploaded lead files and verification results are used."),
    ("terms", "Terms of Use", "Responsible use and verification limitations."),
    ("contact", "Contact", "How to contact the ProveMails administrator."),
]

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        if not request.user.is_superuser:
            return HttpResponseForbidden("Administrator access is required.")
        return view_func(request, *args, **kwargs)
    return wrapper

def _site_settings():
    obj = SiteSettings.objects.get_or_create(pk=1, defaults={"site_url": settings.SITE_URL})[0]
    local_default = "http://127.0.0.1:8000"
    if obj.site_url == local_default and settings.SITE_URL != local_default:
        obj.site_url = settings.SITE_URL
        obj.save(update_fields=["site_url", "updated_at"])
    return obj

def _ensure_starter_pages():
    for slug, title, description in STARTER_PAGES:
        SitePage.objects.get_or_create(
            slug=slug,
            defaults={
                "title": title,
                "seo_title": title + " | ProveMails",
                "meta_description": description,
                "body_text": description + "\n\nEdit this page from the administrator panel.",
                "is_published": True,
            },
        )

def home(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect("dashboard")
    context = {
        "bootstrap_available": (
            not get_user_model().objects.filter(is_superuser=True).exists()
            and bool(settings.PROVEDMAILS_ADMIN_EMAIL)
            and bool(settings.PROVEDMAILS_ADMIN_SIGNUP_KEY)
        )
    }
    return render(request, "home.html", context)

def login_view(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect("dashboard")
    form = AuthenticationForm(request, data=request.POST or None)
    form.fields["username"].label = "Email address"
    form.fields["username"].widget.attrs.update({"autocomplete": "email", "placeholder": "you@example.com"})
    form.fields["password"].widget.attrs.update({"autocomplete": "current-password", "placeholder": "Your password"})
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        if not user.is_superuser:
            messages.error(request, "This workspace is restricted to the administrator.")
        else:
            login(request, user)
            return redirect(request.GET.get("next") or "dashboard")
    return render(request, "login.html", {"form": form})

@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, "You have been signed out.")
    return redirect("home")

def bootstrap_admin(request):
    User = get_user_model()
    if User.objects.filter(is_superuser=True).exists():
        messages.info(request, "The one-time administrator account has already been created. Sign in instead.")
        return redirect("login")
    if not settings.PROVEDMAILS_ADMIN_EMAIL or not settings.PROVEDMAILS_ADMIN_SIGNUP_KEY:
        return render(request, "bootstrap_admin.html", {
            "setup_unavailable": True,
            "configured_email": settings.PROVEDMAILS_ADMIN_EMAIL,
        })
    form = AdminBootstrapForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        # Re-check inside the request so a second bootstrap attempt cannot create another admin.
        if User.objects.filter(is_superuser=True).exists():
            messages.error(request, "The administrator account was already created.")
            return redirect("login")
        email = form.cleaned_data["email"]
        user = User.objects.create_superuser(
            username=email,
            email=email,
            password=form.cleaned_data["password1"],
            first_name=form.cleaned_data["full_name"].strip()[:150],
        )
        login(request, user, backend="leads.auth_backends.EmailBackend")
        messages.success(request, "Your administrator workspace is ready.")
        return redirect("control_dashboard")
    return render(request, "bootstrap_admin.html", {
        "form": form,
        "setup_unavailable": False,
        "configured_email": settings.PROVEDMAILS_ADMIN_EMAIL,
    })

@admin_required
def dashboard(request):
    jobs = EmailJob.objects.filter(owner=request.user)[:12]
    totals = {
        "jobs": EmailJob.objects.filter(owner=request.user).count(),
        "verified": sum(EmailJob.objects.filter(owner=request.user).values_list("completed", flat=True)),
        "valid": sum(EmailJob.objects.filter(owner=request.user).values_list("valid_count", flat=True)),
        "needs_review": sum(EmailJob.objects.filter(owner=request.user).values_list("risky_count", flat=True)) +
                        sum(EmailJob.objects.filter(owner=request.user).values_list("unknown_count", flat=True)),
    }
    return render(request, "dashboard.html", {"jobs": jobs, "totals": totals})

@require_POST
@admin_required
def create_job(request):
    uploaded = request.FILES.get("lead_file")
    if not uploaded:
        messages.error(request, "Choose a CSV or XLSX lead file first.")
        return redirect("dashboard")
    if uploaded.size > settings.MAX_LEAD_FILE_BYTES:
        messages.error(request, "The file is larger than 50 MB. Split the file into smaller batches.")
        return redirect("dashboard")
    suffix = Path(uploaded.name).suffix.lower()
    if suffix not in {".csv", ".xlsx"}:
        messages.error(request, "Supported formats are CSV and XLSX.")
        return redirect("dashboard")
    job = EmailJob.objects.create(
        owner=request.user,
        source_file=uploaded,
        source_filename=Path(uploaded.name).name[:255],
        status=EmailJob.Status.QUEUED,
        phase="queued",
    )
    messages.success(request, "Your file has been queued. Keep the worker running while it verifies the batch.")
    return redirect("job_detail", job_id=job.pk)

@admin_required
def job_detail(request, job_id):
    job = get_object_or_404(EmailJob, pk=job_id, owner=request.user)
    results = job.results.all()[:100] if job.status in {EmailJob.Status.COMPLETED, EmailJob.Status.CANCELED, EmailJob.Status.FAILED} else []
    return render(request, "job_detail.html", {"job": job, "results": results})

@admin_required
def job_status(request, job_id):
    job = get_object_or_404(EmailJob, pk=job_id, owner=request.user)
    return JsonResponse({
        "id": str(job.pk),
        "status": job.status,
        "phase": job.phase,
        "percent": job.progress_percent,
        "completed": job.completed,
        "total": job.total,
        "retry_count": job.retry_count,
        "valid": job.valid_count,
        "invalid": job.invalid_count,
        "risky": job.risky_count,
        "unknown": job.unknown_count,
        "last_log": job.last_log,
        "error": job.error,
        "smtp_available": job.smtp_available,
        "cancel_requested": job.cancel_requested,
        "finished": job.status in {EmailJob.Status.COMPLETED, EmailJob.Status.CANCELED, EmailJob.Status.FAILED},
    })

@require_POST
@admin_required
def cancel_job(request, job_id):
    job = get_object_or_404(EmailJob, pk=job_id, owner=request.user)
    if job.status == EmailJob.Status.QUEUED:
        job.status = EmailJob.Status.CANCELED
        job.phase = "canceled"
        job.cancel_requested = True
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "phase", "cancel_requested", "finished_at", "updated_at"])
        messages.info(request, "The queued job was canceled.")
    elif job.status == EmailJob.Status.RUNNING:
        job.cancel_requested = True
        job.save(update_fields=["cancel_requested", "updated_at"])
        messages.info(request, "Cancellation requested. Active network checks may finish first.")
    else:
        messages.info(request, "This job is no longer running.")
    return redirect("job_detail", job_id=job.pk)

@admin_required
def download_results(request, job_id):
    from itertools import chain
    job = get_object_or_404(EmailJob, pk=job_id, owner=request.user)
    if job.status not in {EmailJob.Status.COMPLETED, EmailJob.Status.CANCELED, EmailJob.Status.FAILED}:
        return HttpResponse("The job is still running.", status=409)
    filter_type = request.GET.get("type", "all").lower()
    allowed = {"all", "valid", "invalid", "risky", "unknown", "non_role"}
    if filter_type not in allowed:
        return HttpResponse("Unsupported result filter.", status=400)
    query = job.results.all().order_by("position")
    if filter_type in {"valid", "invalid", "risky", "unknown"}:
        query = query.filter(status=filter_type)
    iterator = iter(query.iterator(chunk_size=1000))
    first = None
    for candidate in iterator:
        if filter_type == "non_role" and candidate.detail.get("is_role", False):
            continue
        first = candidate
        break
    if first is None:
        return HttpResponse("No result rows match this filter yet.", status=404)

    source_fields = list(first.source_row.keys())
    result_fields = ["verified_email", "status", "reason", "confidence", "is_role", "is_disposable",
                     "is_free", "is_catch_all", "did_you_mean", "mx_host", "provider", "smtp_message",
                     "has_spf", "has_dmarc", "has_gravatar", "reliable"]
    fieldnames = list(dict.fromkeys(source_fields + result_fields))
    base_name = slugify(Path(job.source_filename).stem) or "leads"

    def merged_row(row):
        merged = dict(row.source_row)
        merged.update({"verified_email": row.verified_email, "status": row.status, "reason": row.reason,
                       "confidence": row.confidence, **row.detail})
        return merged

    if request.GET.get("format", "csv").lower() == "xlsx":
        from openpyxl import Workbook
        book = Workbook(write_only=True)
        sheet = book.create_sheet("Verified leads")
        sheet.append(fieldnames)
        for row in chain([first], iterator):
            if filter_type == "non_role" and row.detail.get("is_role", False):
                continue
            merged = merged_row(row)
            sheet.append([merged.get(name, "") if merged.get(name) is not None else "" for name in fieldnames])
        buffer = io.BytesIO()
        book.save(buffer)
        response = HttpResponse(buffer.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = f'attachment; filename="{filter_type}-{base_name}-verified.xlsx"'
        return response

    def csv_chunks():
        buffer = io.StringIO(newline="")
        buffer.write("\ufeff")
        writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        for row in chain([first], iterator):
            if filter_type == "non_role" and row.detail.get("is_role", False):
                continue
            writer.writerow(merged_row(row))
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

    response = StreamingHttpResponse(csv_chunks(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filter_type}-{base_name}-verified.csv"'
    return response

@admin_required
def control_dashboard(request):
    _ensure_starter_pages()
    jobs = EmailJob.objects.all()
    stats = {
        "jobs": jobs.count(),
        "active": jobs.filter(status__in=[EmailJob.Status.QUEUED, EmailJob.Status.RUNNING]).count(),
        "completed": jobs.filter(status=EmailJob.Status.COMPLETED).count(),
        "leads": sum(jobs.values_list("total", flat=True)),
        "pages": SitePage.objects.count(),
    }
    return render(request, "control/dashboard.html", {"stats": stats, "latest_jobs": jobs[:10]})

@admin_required
def control_settings(request):
    settings_obj = _site_settings()
    is_settings_post = request.method == "POST" and request.POST.get("action") == "save_settings"
    is_verification_post = request.method == "POST" and request.POST.get("action") == "upload_verification"
    settings_form = SiteSettingsForm(request.POST if is_settings_post else None, instance=settings_obj, prefix="site")
    verification_form = SearchConsoleFileForm(request.POST if is_verification_post else None, request.FILES if is_verification_post else None, prefix="verification")
    if is_settings_post:
        if settings_form.is_valid():
            settings_form.save()
            messages.success(request, "Site settings and SEO metadata were saved.")
            return redirect("control_settings")
    elif is_verification_post:
        if verification_form.is_valid():
            uploaded = verification_form.cleaned_data["verification_file"]
            content = uploaded.read().decode("utf-8-sig")
            SearchConsoleVerification.objects.update_or_create(
                filename=Path(uploaded.name).name,
                defaults={"file_content": content},
            )
            messages.success(request, f"Search Console verification file is now served at /{uploaded.name}.")
            return redirect("control_settings")
    verification_files = SearchConsoleVerification.objects.all().order_by("-uploaded_at")
    return render(request, "control/settings.html", {
        "settings_form": settings_form,
        "verification_form": verification_form,
        "verification_files": verification_files,
    })

@admin_required
def control_pages(request):
    _ensure_starter_pages()
    return render(request, "control/pages.html", {"pages": SitePage.objects.all()})

@admin_required
def edit_page(request, slug):
    _ensure_starter_pages()
    page = get_object_or_404(SitePage, slug=slug)
    form = SitePageForm(request.POST or None, instance=page)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "The page and its SEO metadata were saved.")
        return redirect("control_pages")
    return render(request, "control/page_edit.html", {"page": page, "form": form})

def public_page(request, slug):
    _ensure_starter_pages()
    page = get_object_or_404(SitePage, slug=slug)
    if not page.is_published and not (request.user.is_authenticated and request.user.is_superuser):
        from django.http import Http404
        raise Http404()
    return render(request, "page.html", {"page": page})

def robots_txt(request):
    site_url = (_site_settings().site_url or settings.SITE_URL).rstrip("/")
    text = "\n".join([
        "User-agent: *",
        "Allow: /",
        "Disallow: /dashboard/",
        "Disallow: /jobs/",
        "Disallow: /control/",
        "Disallow: /django-admin/",
        "Disallow: /login/",
        "Disallow: /admin-signup/",
        f"Sitemap: {site_url}/sitemap.xml",
        "",
    ])
    return HttpResponse(text, content_type="text/plain")

def sitemap_xml(request):
    site_url = (_site_settings().site_url or settings.SITE_URL).rstrip("/")
    paths = ["/"]
    paths += [f"/pages/{p.slug}/" for p in SitePage.objects.filter(is_published=True).order_by("slug")]
    urls = "".join(f"<url><loc>{escape(site_url + path)}</loc></url>" for path in paths)
    xml = '<?xml version="1.0" encoding="UTF-8"?>' + '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + urls + "</urlset>"
    return HttpResponse(xml, content_type="application/xml")

def search_console_verification(request, filename):
    if not re.fullmatch(r"google[A-Za-z0-9_-]+\.html", filename, flags=re.IGNORECASE):
        return HttpResponse("Not found", status=404)
    item = get_object_or_404(SearchConsoleVerification, filename=filename)
    return HttpResponse(item.file_content, content_type="text/html; charset=utf-8")
