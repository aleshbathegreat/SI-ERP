"""CSV master data migration loader."""

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.models import Organization
from finance.models import Account, FixedAsset, JournalEntry, JournalLine, Vendor
from hr.models import Department, Designation, Employee, LeaveBalance, LeaveType


class Command(BaseCommand):
    help = (
        "Import CoA/employees/vendors/leave balances/assets/opening journals. "
        "Usage: import_masters --org jmc --coa file.csv"
    )

    def add_arguments(self, parser):
        parser.add_argument("--org", required=True, help="Organization code")
        parser.add_argument("--coa", help="Chart of accounts CSV: code,name,account_type")
        parser.add_argument("--vendors", help="Vendors CSV: name,ntn,email,phone")
        parser.add_argument(
            "--employees",
            help="Employees CSV: employee_code,first_name,last_name,email,basic_salary,dept_code,desig_code",
        )
        parser.add_argument(
            "--leave-balances",
            help="CSV: employee_code,leave_type_code,year,opening,accrued,used,encashed,carried_forward",
        )
        parser.add_argument(
            "--assets",
            help="CSV: asset_code,name,category,purchase_date,purchase_cost,depreciation_rate,book_value,location",
        )
        parser.add_argument(
            "--opening-journals",
            help="CSV: entry_date,reference,account_code,debit,credit,description (grouped by reference)",
        )

    def handle(self, *args, **options):
        org = Organization.objects.filter(code=options["org"]).first()
        if not org:
            raise CommandError(f"Unknown org {options['org']}")
        if options.get("coa"):
            self._coa(org, Path(options["coa"]))
        if options.get("vendors"):
            self._vendors(org, Path(options["vendors"]))
        if options.get("employees"):
            self._employees(org, Path(options["employees"]))
        if options.get("leave_balances"):
            self._leave_balances(org, Path(options["leave_balances"]))
        if options.get("assets"):
            self._assets(org, Path(options["assets"]))
        if options.get("opening_journals"):
            self._opening_journals(org, Path(options["opening_journals"]))
        self.stdout.write(self.style.SUCCESS("Import complete"))

    def _coa(self, org, path):
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                Account.objects.update_or_create(
                    organization=org,
                    code=row["code"].strip(),
                    defaults={
                        "name": row["name"].strip(),
                        "account_type": row.get("account_type", "asset").strip(),
                    },
                )
        self.stdout.write(f"CoA imported from {path}")

    def _vendors(self, org, path):
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                Vendor.objects.update_or_create(
                    organization=org,
                    name=row["name"].strip(),
                    defaults={
                        "ntn": row.get("ntn", ""),
                        "email": row.get("email", ""),
                        "phone": row.get("phone", ""),
                    },
                )
        self.stdout.write(f"Vendors imported from {path}")

    def _employees(self, org, path):
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                dept = None
                desig = None
                if row.get("dept_code"):
                    dept, _ = Department.objects.get_or_create(
                        organization=org,
                        code=row["dept_code"].strip(),
                        defaults={"name": row["dept_code"].strip()},
                    )
                if row.get("desig_code"):
                    desig, _ = Designation.objects.get_or_create(
                        organization=org,
                        code=row["desig_code"].strip(),
                        defaults={"title": row["desig_code"].strip()},
                    )
                Employee.objects.update_or_create(
                    organization=org,
                    employee_code=row["employee_code"].strip(),
                    defaults={
                        "first_name": row["first_name"].strip(),
                        "last_name": row["last_name"].strip(),
                        "email": row.get("email", f"{row['employee_code']}@imported.local"),
                        "basic_salary": Decimal(row.get("basic_salary") or "0"),
                        "department": dept,
                        "designation": desig,
                    },
                )
        self.stdout.write(f"Employees imported from {path}")

    def _leave_balances(self, org, path):
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                emp = Employee.objects.filter(
                    organization=org, employee_code=row["employee_code"].strip()
                ).first()
                if not emp:
                    self.stderr.write(f"Skip unknown employee {row.get('employee_code')}")
                    continue
                lt, _ = LeaveType.objects.get_or_create(
                    organization=org,
                    code=row["leave_type_code"].strip(),
                    defaults={"name": row["leave_type_code"].strip()},
                )
                year = int(row.get("year") or date.today().year)
                LeaveBalance.objects.update_or_create(
                    organization=org,
                    employee=emp,
                    leave_type=lt,
                    year=year,
                    defaults={
                        "opening": Decimal(row.get("opening") or "0"),
                        "accrued": Decimal(row.get("accrued") or "0"),
                        "used": Decimal(row.get("used") or "0"),
                        "encashed": Decimal(row.get("encashed") or "0"),
                        "carried_forward": Decimal(row.get("carried_forward") or "0"),
                    },
                )
        self.stdout.write(f"Leave balances imported from {path}")

    def _assets(self, org, path):
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                cost = Decimal(row.get("purchase_cost") or "0")
                book = Decimal(row.get("book_value") or cost)
                pd = None
                if row.get("purchase_date"):
                    try:
                        pd = date.fromisoformat(row["purchase_date"].strip()[:10])
                    except ValueError:
                        pd = None
                FixedAsset.objects.update_or_create(
                    organization=org,
                    asset_code=row["asset_code"].strip(),
                    defaults={
                        "name": row.get("name", row["asset_code"]).strip(),
                        "category": row.get("category", ""),
                        "location": row.get("location", ""),
                        "purchase_date": pd,
                        "purchase_cost": cost,
                        "depreciation_rate": Decimal(row.get("depreciation_rate") or "0"),
                        "book_value": book,
                        "status": "active",
                    },
                )
        self.stdout.write(f"Assets imported from {path}")

    def _opening_journals(self, org, path):
        # Group lines by reference
        groups: dict[str, list] = {}
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                ref = (row.get("reference") or "OPENING").strip()
                groups.setdefault(ref, []).append(row)
        created = 0
        for ref, rows in groups.items():
            if JournalEntry.objects.filter(organization=org, reference=ref).exists():
                continue
            first = rows[0]
            try:
                ed = date.fromisoformat((first.get("entry_date") or date.today().isoformat())[:10])
            except ValueError:
                ed = date.today()
            je = JournalEntry.objects.create(
                organization=org,
                entry_date=ed,
                reference=ref,
                narration=f"Opening balance {ref}",
                status=JournalEntry.Status.POSTED,
            )
            for row in rows:
                acct = Account.objects.filter(
                    organization=org, code=row["account_code"].strip()
                ).first()
                if not acct:
                    self.stderr.write(f"Skip unknown account {row.get('account_code')}")
                    continue
                JournalLine.objects.create(
                    journal=je,
                    account=acct,
                    debit=Decimal(row.get("debit") or "0"),
                    credit=Decimal(row.get("credit") or "0"),
                    description=row.get("description", ""),
                )
            created += 1
        self.stdout.write(f"Opening journals created: {created} from {path}")
