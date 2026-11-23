from datetime import date

from django.core.management.base import BaseCommand

from core.jobs import bill_due_customer_contracts


class Command(BaseCommand):
    help = "Generate draft AR invoices for recurring customer contracts due today or earlier"

    def add_arguments(self, parser):
        parser.add_argument("--date", help="Bill as of YYYY-MM-DD (default: today)")

    def handle(self, *args, **options):
        today = date.fromisoformat(options["date"]) if options.get("date") else None
        stats = bill_due_customer_contracts(today)
        self.stdout.write(self.style.SUCCESS(str(stats)))
