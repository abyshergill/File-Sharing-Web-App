from django.core.management.base import BaseCommand
from django.template.defaultfilters import filesizeformat

from sharing.models import ActivityLog
from sharing.services import delete_shared_files, old_files_queryset


class Command(BaseCommand):
    help = "Delete shared files older than N days (for use from cron)."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, days, dry_run, **options):
        qs = old_files_queryset(days)
        if dry_run:
            self.stdout.write(f"{qs.count()} file(s) older than {days} days would be deleted.")
            return
        count, freed = delete_shared_files(qs)
        ActivityLog.objects.create(
            action=ActivityLog.Action.CLEANUP,
            username="system",
            details=f"Scheduled cleanup: deleted {count} file(s) older than {days} days, freed {filesizeformat(freed)}",
        )
        self.stdout.write(self.style.SUCCESS(f"Deleted {count} file(s), freed {filesizeformat(freed)}."))
