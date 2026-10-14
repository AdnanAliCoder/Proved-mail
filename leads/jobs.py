import time
from django.utils import timezone
from .models import EmailJob, VerificationRow
from .services import read_lead_file
from verifier.engine import run_batch
from verifier.smtp_probe import is_smtp_available

def process_job(job_id):
    job = EmailJob.objects.get(pk=job_id)
    if job.status == EmailJob.Status.CANCELED:
        return
    job.status = EmailJob.Status.RUNNING
    job.phase = "starting"
    job.started_at = timezone.now()
    job.error = ""
    job.save(update_fields=["status", "phase", "started_at", "error", "updated_at"])
    try:
        if not job.source_file:
            raise ValueError("The original upload file is missing.")
        headers, rows, email_field = read_lead_file(job.source_file.path, job.source_filename)
        job.total = len(rows)
        job.email_field = email_field
        job.phase = "pass1"
        job.save(update_fields=["total", "email_field", "phase", "updated_at"])
        try:
            job.smtp_available = is_smtp_available()
        except Exception:
            job.smtp_available = False
        job.save(update_fields=["smtp_available", "updated_at"])

        last_write = {"completed": -1, "checked_at": 0.0}
        def on_progress(completed, progress_total, result):
            now = time.monotonic()
            if completed == progress_total or completed % 10 == 0 or now - last_write["checked_at"] >= 1.5:
                EmailJob.objects.filter(pk=job.pk, status=EmailJob.Status.RUNNING).update(
                    completed=min(job.total, completed),
                    last_log=f"{result.email} -> {result.status} ({result.reason})"[:320],
                    updated_at=timezone.now(),
                )
                last_write["completed"] = completed
                last_write["checked_at"] = now

        def on_phase(phase, extra):
            EmailJob.objects.filter(pk=job.pk).update(
                phase=phase,
                retry_count=int(extra.get("retry_count", 0)),
                updated_at=timezone.now(),
            )

        cancel_cache = {"checked_at": 0.0, "value": False}
        def should_cancel():
            now = time.monotonic()
            if now - cancel_cache["checked_at"] > 1.0:
                cancel_cache["checked_at"] = now
                cancel_cache["value"] = EmailJob.objects.filter(pk=job.pk).values_list("cancel_requested", flat=True).first() is True
            return cancel_cache["value"]

        results = run_batch(rows, email_field, on_progress, should_cancel, on_phase)
        VerificationRow.objects.filter(job=job).delete()
        objects = []
        counts = {"valid": 0, "invalid": 0, "risky": 0, "unknown": 0}
        for position, (source_row, result) in enumerate(zip(rows, results), start=1):
            if result is None:
                continue
            status = result.status or "unknown"
            counts[status] = counts.get(status, 0) + 1
            objects.append(VerificationRow(
                job=job,
                position=position,
                source_row=source_row,
                verified_email=result.email or "",
                status=status,
                reason=result.reason or "",
                confidence=max(0, min(100, int(result.confidence or 0))),
                detail=result.as_row(),
            ))
            if len(objects) >= 1000:
                VerificationRow.objects.bulk_create(objects, batch_size=500)
                objects = []
        if objects:
            VerificationRow.objects.bulk_create(objects, batch_size=500)

        job.refresh_from_db()
        job.valid_count = counts.get("valid", 0)
        job.invalid_count = counts.get("invalid", 0)
        job.risky_count = counts.get("risky", 0)
        job.unknown_count = counts.get("unknown", 0)
        if job.cancel_requested or any(item is None for item in results):
            job.status = EmailJob.Status.CANCELED
            job.phase = "canceled"
        else:
            job.status = EmailJob.Status.COMPLETED
            job.phase = "done"
        job.completed = sum(counts.values())
        job.finished_at = timezone.now()
        job.save(update_fields=[
            "valid_count", "invalid_count", "risky_count", "unknown_count",
            "status", "phase", "completed", "finished_at", "updated_at",
        ])
    except Exception as exc:
        job.status = EmailJob.Status.FAILED
        job.phase = "failed"
        job.error = str(exc)[:2000]
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "phase", "error", "finished_at", "updated_at"])
