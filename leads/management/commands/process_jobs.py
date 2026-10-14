import time
from django.core.management.base import BaseCommand
from django.db import close_old_connections
from leads.models import EmailJob
from leads.jobs import process_job

class Command(BaseCommand):
    help = "Process queued ProveMails verification jobs. Run one worker process."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Process currently queued jobs and exit.")
        parser.add_argument("--poll-seconds", type=float, default=2.0)

    def handle(self, *args, **options):
        # A previous worker may have stopped unexpectedly. Jobs are restartable from the original upload.
        recovered = EmailJob.objects.filter(status=EmailJob.Status.RUNNING).update(
            status=EmailJob.Status.QUEUED,
            phase="queued",
            completed=0,
            error="Recovered after worker restart; the file will be processed again.",
        )
        if recovered:
            self.stdout.write(self.style.WARNING(f"Re-queued {recovered} interrupted job(s)."))
        self.stdout.write(self.style.SUCCESS("ProveMails queue worker is ready."))
        while True:
            close_old_connections()
            job = EmailJob.objects.filter(status=EmailJob.Status.QUEUED).order_by("created_at").first()
            if job is None:
                if options["once"]:
                    return
                time.sleep(max(0.5, options["poll_seconds"]))
                continue
            if job.cancel_requested:
                job.status = EmailJob.Status.CANCELED
                job.phase = "canceled"
                job.finished_at = __import__("django.utils.timezone", fromlist=["now"]).now()
                job.save(update_fields=["status", "phase", "finished_at", "updated_at"])
                continue
            self.stdout.write(f"Processing {job.source_filename} ({job.pk})")
            try:
                process_job(job.pk)
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"Job {job.pk} failed: {exc}"))
            if options["once"]:
                return
