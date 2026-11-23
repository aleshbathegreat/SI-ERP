from django.core.management.base import BaseCommand

from core.subscription_lifecycle import run_expiry_pass


class Command(BaseCommand):
    help = "Mark expired trials/subscriptions past_due/canceled, overdue invoices, dunning mail"

    def add_arguments(self, parser):
        parser.add_argument("--no-mail", action="store_true", help="Skip dunning emails")
        parser.add_argument(
            "--cooldown-hours",
            type=int,
            default=48,
            help="Minimum hours between dunning emails per tenant",
        )

    def handle(self, *args, **options):
        stats = run_expiry_pass(
            send_mail=not options["no_mail"],
            dunning_cooldown_hours=options["cooldown_hours"],
        )
        self.stdout.write(self.style.SUCCESS(str(stats)))
