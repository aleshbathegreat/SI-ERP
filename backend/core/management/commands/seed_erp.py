"""Full-fledged JMC demo tenant seeder (Finance / HR / Payroll + LoA samples)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Role, UserProfile, UserRole
from accounts.rbac import ensure_default_roles
from core.access import ensure_default_packages, start_trial
from core.models import (
    AuditLog,
    CompanyLink,
    Organization,
    PayFastSettings,
    PlatformSmtpSettings,
    SubscriptionPackage,
    SubscriptionPayment,
    TenantEmailProfile,
    TenantPayGateway,
    TenantSmtpSettings,
)
from finance.models import (
    Account,
    AccountingPeriod,
    BankAccount,
    BankReconciliation,
    BankStatementLine,
    Budget,
    CostCenter,
    FixedAsset,
    Investment,
    JournalEntry,
    JournalLine,
    TaxChallan,
    TaxCode,
    Vendor,
    VendorInvoice,
)
from hr.models import (
    AttendanceDevice,
    AttendanceRecord,
    BenefitPlan,
    Department,
    Designation,
    Employee,
    EmployeeBenefit,
    EmployeeDocument,
    LeaveRequest,
    LeaveType,
    PerformanceReview,
    ProbationRecord,
    RecruitmentRequest,
    SeparationRecord,
    TrainingRecord,
)
from payroll.models import PayrollPeriod, Payslip, SalaryStructure


class Command(BaseCommand):
    help = "Seed full JMC demo tenant with Finance, HR, Payroll and LoA sample data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-demo",
            action="store_true",
            help="Delete existing jmc org transactional rows before reseeding (keeps users)",
        )

    def handle(self, *args, **options):
        ensure_default_packages()
        today = date.today()
        year = today.year

        packages = self._subscription_packages()
        platform_pf, platform_smtp = self._platform_gateways()

        org = self._org()
        if options.get("reset_demo"):
            self._wipe_transactions(org)

        admin, users = self._users(org)
        self._tenant_gateways(org)
        self._subscription_demo(org, admin, packages, today)
        accounts, centers = self._finance_masters(org, year)
        self._finance_transactions(org, accounts, centers, users, today, year)
        depts, desigs, employees, leave_types = self._hr(org, users, today)
        self._payroll(org, employees, today)
        self._email_profiles(org)
        AuditLog.objects.get_or_create(
            organization=org,
            user=admin,
            action="seed",
            module="settings.audit",
            defaults={
                "detail": (
                    f"Full JMC demo seed · employees={employees.count()} · "
                    f"depts={depts} · designations={desigs} · leave_types={leave_types} · "
                    f"packages={packages} · payfast={platform_pf} · smtp={platform_smtp}"
                )
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nJMC full demo ready | tenant={org.code} | trial_ends={org.trial_ends}\n"
                f"  Brand: {org.brand_name or org.name}\n"
                f"  Plans: {packages} · Platform PayFast: {platform_pf} · Platform SMTP: {platform_smtp}\n"
                "  Subdomain tip: jmc.<PLATFORM_ROOT_DOMAIN>\n\n"
                "Logins:\n"
                "  platform / Platform@123    (Platform owner · SaaS control center)\n"
                "  admin / Admin@123          (Tenant owner · no platform screens)\n"
                "  fin.mgr / Fin@12345        (Finance)\n"
                "  hr.mgr / Hr@12345          (HR)\n"
                "  pay.officer / Pay@12345    (Payroll)\n"
                "  approver1 / App@12345      (Approver / LoA)\n"
                "  initiator1 / Init@12345    (Initiator)\n"
                "  ess.user / Ess@12345       (ESS - linked to EMP-001)\n"
                "  auditor1 / Aud@12345       (Auditor)\n"
            )
        )

    def _subscription_packages(self) -> int:
        """Ensure SaaS catalog (trial / monthly / annual) is present and active."""
        ensure_default_packages()
        # Force-refresh catalog fields so demos always see current copy/limits.
        specs = [
            (
                "trial",
                "Trial",
                Decimal("0"),
                SubscriptionPackage.Interval.TRIAL,
                0,
                10,
                25,
                "14-day full ERP trial. Finance, HR and Payroll included.",
            ),
            (
                "monthly",
                "Monthly",
                Decimal("7500"),
                SubscriptionPackage.Interval.MONTH,
                1,
                10,
                50,
                "Billed monthly. Full Finance, HR and Payroll SaaS access.",
            ),
            (
                "annual",
                "Annual",
                Decimal("75000"),
                SubscriptionPackage.Interval.YEAR,
                2,
                25,
                200,
                "Billed yearly (2 months included). Full ERP module access.",
            ),
            (
                "enterprise",
                "Enterprise",
                Decimal("150000"),
                SubscriptionPackage.Interval.YEAR,
                3,
                100,
                1000,
                "Annual enterprise seat pack with priority support.",
            ),
        ]
        modules = [
            "dashboard",
            "finance",
            "hr",
            "payroll",
            "ops",
            "billing",
        ]
        for code, name, price, interval, sort, max_fu, max_ess, summary in specs:
            SubscriptionPackage.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "price": price,
                    "interval": interval,
                    "summary": summary,
                    "module_keys": modules,
                    "max_functional_users": max_fu,
                    "max_ess_users": max_ess,
                    "active": True,
                    "sort": sort,
                },
            )
        return SubscriptionPackage.objects.filter(active=True).count()

    def _platform_gateways(self):
        """Platform PayFast (sandbox placeholders) + SMTP profile for billing emails."""
        pf = PayFastSettings.load()
        # Demo sandbox placeholders — replace via Platform → PayFast settings for real checkout.
        if not pf.sandbox_merchant_id:
            pf.environment = PayFastSettings.Environment.SANDBOX
            pf.sandbox_api_base = "https://ipguat.apps.net.pk/Ecommerce/api"
            pf.sandbox_merchant_id = "102"
            pf.sandbox_secured_key = "zW1AVA67oiBVGe9I"
            pf.sandbox_hash_key = "ThisIsHashKey"
            pf.live_api_base = "https://ipg1.apps.net.pk/Ecommerce/api"
            pf.save()
            pf_label = "sandbox seeded"
        else:
            pf_label = f"{pf.environment} (kept)"

        smtp = PlatformSmtpSettings.load()
        if not smtp.host:
            smtp.host = "smtp.office365.com"
            smtp.port = 587
            smtp.username = "noreply@mushaz.com"
            smtp.password = ""
            smtp.use_tls = True
            smtp.use_ssl = False
            smtp.from_email = "noreply@mushaz.com"
            smtp.from_name = "SIGBL ERP"
            smtp.reply_to = "support@mushaz.com"
            smtp.is_active = False  # enable after setting real password
            smtp.save()
            smtp_label = "profile seeded (inactive)"
        else:
            smtp_label = "kept"
        return pf_label, smtp_label

    def _tenant_gateways(self, org: Organization):
        gw, created = TenantPayGateway.objects.get_or_create(organization=org)
        if created or not gw.sandbox_merchant_id:
            gw.environment = TenantPayGateway.Environment.SANDBOX
            gw.sandbox_api_base = "https://ipguat.apps.net.pk/Ecommerce/api"
            gw.sandbox_merchant_id = "102"
            gw.sandbox_secured_key = "zW1AVA67oiBVGe9I"
            gw.sandbox_hash_key = "ThisIsHashKey"
            gw.live_api_base = "https://ipg1.apps.net.pk/Ecommerce/api"
            gw.save()

        smtp, created = TenantSmtpSettings.objects.get_or_create(organization=org)
        if created or not smtp.host:
            smtp.host = "smtp.office365.com"
            smtp.port = 587
            smtp.username = "erp@jmc.local"
            smtp.password = ""
            smtp.use_tls = True
            smtp.from_email = "erp@jmc.local"
            smtp.from_name = "JMC ERP"
            smtp.reply_to = "erp@jmc.local"
            smtp.is_active = False
            smtp.save()

    def _subscription_demo(self, org: Organization, admin, packages: int, today: date):
        """Attach trial package + sample billing payment history for Billing UI."""
        trial = SubscriptionPackage.objects.filter(code="trial").first()
        monthly = SubscriptionPackage.objects.filter(code="monthly").first()
        if trial and not org.package_id:
            org.package = trial
            org.save(update_fields=["package", "updated_at"])
        if not org.trial_ends and not org.subscription_ends:
            start_trial(org, days=90)
        elif org.trial_ends and org.trial_ends < today:
            start_trial(org, days=90)

        # Sample paid trial→monthly style history (does not change current trial plan)
        if monthly and not SubscriptionPayment.objects.filter(
            organization=org, reference="DEMO-SEED-MONTHLY-1"
        ).exists():
            SubscriptionPayment.objects.create(
                organization=org,
                user=admin,
                plan="monthly",
                kind=SubscriptionPayment.Kind.NEW,
                period_start=today - timedelta(days=120),
                period_end=today - timedelta(days=90),
                amount=monthly.price,
                currency="PKR",
                reference="DEMO-SEED-MONTHLY-1",
                basket_id="DEMO-BASKET-001",
                transaction_id="DEMO-TXN-001",
                environment="sandbox",
                status=SubscriptionPayment.Status.PAID,
                status_code="00",
                status_message="Demo seed payment",
                notes="Seeded sample PayFast success",
            )
        if monthly and not SubscriptionPayment.objects.filter(
            organization=org, reference="DEMO-SEED-PENDING-1"
        ).exists():
            SubscriptionPayment.objects.create(
                organization=org,
                user=admin,
                plan="annual",
                kind=SubscriptionPayment.Kind.UPGRADE,
                period_start=today,
                period_end=today + timedelta(days=365),
                amount=Decimal("75000"),
                currency="PKR",
                reference="DEMO-SEED-PENDING-1",
                basket_id="DEMO-BASKET-002",
                environment="sandbox",
                status=SubscriptionPayment.Status.PENDING,
                notes="Seeded sample pending checkout",
            )

    def _org(self) -> Organization:
        org, _ = Organization.objects.update_or_create(
            code="jmc",
            defaults={
                "name": "Jinnah Medical Construction Company",
                "email": "erp@jmc.local",
                "phone": "+92-51-111-562-562",
                "address": "Blue Area, Islamabad, Pakistan",
                "ntn": "1234567-8",
                "strn": "3277876123456",
                "timezone": "Asia/Karachi",
                "is_active": True,
                "brand_name": "JMC ERP",
                "brand_tagline": "Accounts · HR · Payroll",
                "brand_primary_color": "#0B3D5C",
                "brand_secondary_color": "#C45C26",
            },
        )
        if not org.trial_ends and not org.subscription_ends:
            start_trial(org, days=90)
        elif org.trial_ends and org.trial_ends < date.today():
            start_trial(org, days=90)
        return org

    def _wipe_transactions(self, org: Organization):
        JournalLine.objects.filter(journal__organization=org).delete()
        JournalEntry.objects.filter(organization=org).delete()
        VendorInvoice.objects.filter(organization=org).delete()
        Budget.objects.filter(organization=org).delete()
        BankStatementLine.objects.filter(organization=org).delete()
        BankReconciliation.objects.filter(organization=org).delete()
        Payslip.objects.filter(period__organization=org).delete()
        LeaveRequest.objects.filter(employee__organization=org).delete()
        AttendanceRecord.objects.filter(organization=org).delete()
        self.stdout.write("Cleared prior JMC transactional demo rows")

    def _users(self, org: Organization):
        ensure_default_roles(org)
        owner_role = Role.objects.filter(organization=org, code="owner").first()

        # Dedicated SaaS platform owner (no tenant ERP ownership)
        platform, p_created = User.objects.get_or_create(
            username="platform",
            defaults={
                "email": "platform@sigbl.com",
                "first_name": "Platform",
                "last_name": "Owner",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if p_created:
            platform.set_password("Platform@123")
            platform.save()
        else:
            platform.is_staff = True
            platform.is_superuser = True
            platform.save(update_fields=["is_staff", "is_superuser"])
        # Platform user must not be bound as a tenant member
        UserProfile.objects.filter(user=platform).delete()
        CompanyLink.objects.filter(user=platform).delete()
        UserRole.objects.filter(user=platform).delete()

        # Tenant owner — never a platform superuser
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@sigbl.com",
                "first_name": "ERP",
                "last_name": "Admin",
                "is_staff": True,
                "is_superuser": False,
            },
        )
        if created:
            admin.set_password("Admin@123")
            admin.save()
        else:
            admin.is_staff = True
            admin.is_superuser = False
            admin.save(update_fields=["is_staff", "is_superuser"])

        org.owner = admin
        org.save(update_fields=["owner", "updated_at"])

        UserProfile.objects.update_or_create(
            user=admin,
            defaults={
                "organization": org,
                "role": UserProfile.RoleCode.OWNER,
                "designation": "Organizational Super User",
                "primary_role": owner_role,
                "phone": "03001234567",
            },
        )
        if owner_role:
            UserRole.objects.get_or_create(user=admin, role=owner_role)
        CompanyLink.objects.get_or_create(user=admin, organization=org)

        demo_users = [
            ("fin.mgr", "finance", "Ayesha", "Finance", "fin.mgr@jmc.local", "Fin@12345", "03011110001"),
            ("hr.mgr", "hr", "Bilal", "HR", "hr.mgr@jmc.local", "Hr@12345", "03011110002"),
            ("pay.officer", "payroll", "Sana", "Payroll", "pay@jmc.local", "Pay@12345", "03011110003"),
            ("approver1", "approver", "Imran", "Approver", "approver@jmc.local", "App@12345", "03011110004"),
            ("initiator1", "initiator", "Nadia", "Initiator", "init@jmc.local", "Init@12345", "03011110005"),
            ("ess.user", "employee", "Ali", "Khan", "ess@jmc.local", "Ess@12345", "03011110006"),
            ("auditor1", "viewer", "Omar", "Auditor", "audit@jmc.local", "Aud@12345", "03011110007"),
        ]
        by_username = {"admin": admin}
        for username, code, first, last, email, password, phone in demo_users:
            u, was_created = User.objects.get_or_create(
                username=username,
                defaults={"email": email, "first_name": first, "last_name": last},
            )
            if was_created:
                u.set_password(password)
                u.save()
            else:
                u.first_name = first
                u.last_name = last
                u.email = email
                u.save(update_fields=["first_name", "last_name", "email"])
            role = Role.objects.filter(organization=org, code=code).first()
            profile_role = (
                code if code in dict(UserProfile.RoleCode.choices) else "employee"
            )
            UserProfile.objects.update_or_create(
                user=u,
                defaults={
                    "organization": org,
                    "role": profile_role,
                    "primary_role": role,
                    "designation": f"{first} {last}",
                    "phone": phone,
                },
            )
            UserRole.objects.filter(user=u, role__organization=org).delete()
            if role:
                UserRole.objects.get_or_create(user=u, role=role)
            CompanyLink.objects.get_or_create(user=u, organization=org)
            by_username[username] = u
        return admin, by_username

    def _finance_masters(self, org: Organization, year: int):
        chart = [
            ("1000", "Cash in Hand", "asset"),
            ("1010", "Cash at Bank — HBL", "asset"),
            ("1020", "Cash at Bank — Meezan", "asset"),
            ("1100", "Accounts Receivable", "asset"),
            ("1200", "Advances & Prepayments", "asset"),
            ("1500", "Furniture & Fixtures", "asset"),
            ("1510", "IT Equipment", "asset"),
            ("1520", "Vehicles", "asset"),
            ("1530", "Accumulated Depreciation", "asset"),
            ("1600", "Investments / TDRs", "asset"),
            ("2000", "Accounts Payable", "liability"),
            ("2100", "Withholding Tax Payable", "liability"),
            ("2110", "Sales Tax Payable", "liability"),
            ("2200", "Accrued Expenses", "liability"),
            ("2300", "Staff Payable", "liability"),
            ("3000", "Share Capital / Fund Balance", "equity"),
            ("3100", "Retained Earnings", "equity"),
            ("4000", "Contract Revenue", "income"),
            ("4100", "Grant / Donor Income", "income"),
            ("4200", "Other Income", "income"),
            ("5000", "Salaries & Wages", "expense"),
            ("5100", "Project Materials", "expense"),
            ("5200", "Subcontractor Costs", "expense"),
            ("5300", "Utilities & Occupancy", "expense"),
            ("5400", "Travel & Conveyance", "expense"),
            ("5500", "Professional Fees", "expense"),
            ("5600", "Depreciation Expense", "expense"),
            ("5700", "Bank Charges", "expense"),
            ("5800", "Misc Operating Expense", "expense"),
        ]
        accounts = {}
        for code, name, atype in chart:
            acc, _ = Account.objects.get_or_create(
                organization=org,
                code=code,
                defaults={"name": name, "account_type": atype, "is_active": True},
            )
            accounts[code] = acc

        centers = {}
        for code, name in [
            ("HO", "Head Office — Islamabad"),
            ("SITE-LHR", "Lahore Site"),
            ("SITE-KHI", "Karachi Site"),
            ("SITE-ISB", "Islamabad Site"),
            ("ADMIN", "Administration"),
            ("HR", "Human Resources CC"),
        ]:
            cc, _ = CostCenter.objects.get_or_create(
                organization=org, code=code, defaults={"name": name, "is_active": True}
            )
            centers[code] = cc

        for code, name, rate, ttype in [
            ("WHT-10", "Withholding Tax 10%", "10", "wht"),
            ("WHT-4", "Withholding Tax 4%", "4", "wht"),
            ("ST-18", "Sales Tax 18%", "18", "st"),
            ("ST-0", "Exempt / Zero-rated", "0", "st"),
        ]:
            TaxCode.objects.get_or_create(
                organization=org,
                code=code,
                defaults={
                    "name": name,
                    "tax_type": ttype,
                    "rate_percent": Decimal(rate),
                    "is_active": True,
                },
            )

        for i in range(1, 13):
            AccountingPeriod.objects.get_or_create(
                organization=org,
                year=year,
                month=i,
                defaults={
                    "name": date(year, i, 1).strftime("%B %Y"),
                    "is_locked": i < date.today().month - 1,
                },
            )

        return accounts, centers

    def _finance_transactions(self, org, accounts, centers, users, today, year):
        vendors_spec = [
            ("Al-Noor Construction Supplies", "1111111-1", "supplies", "051-1111111"),
            ("Pak Steel Traders", "2222222-2", "materials", "042-2222222"),
            ("Skyline Consultants", "3333333-3", "services", "021-3333333"),
            ("Green Power Solutions", "4444444-4", "utilities", "051-4444444"),
            ("SafeGuard Security", "5555555-5", "services", "051-5555555"),
            ("Office Mart (Pvt) Ltd", "6666666-6", "admin", "051-6666666"),
            ("Heavy Plant Rentals", "7777777-7", "equipment", "042-7777777"),
            ("Digital Print House", "8888888-8", "admin", "051-8888888"),
            ("Karachi Logistics Co", "9999999-9", "logistics", "021-9999999"),
            ("Demo Vendor (Pvt) Ltd", "1234567-8", "services", "051-0000000"),
        ]
        vendors = []
        for name, ntn, cat, phone in vendors_spec:
            v, _ = Vendor.objects.get_or_create(
                organization=org,
                name=name,
                defaults={
                    "ntn": ntn,
                    "email": f"{name.split()[0].lower()}@vendor.local",
                    "phone": phone,
                    "category": cat,
                    "address": "Pakistan",
                    "is_active": True,
                },
            )
            vendors.append(v)

        bank_hbl, _ = BankAccount.objects.get_or_create(
            organization=org,
            account_no="PK36HABB0000123456701234",
            defaults={
                "name": "JMC Operating — HBL",
                "bank_name": "Habib Bank Limited",
                "currency": "PKR",
                "opening_balance": Decimal("5000000"),
            },
        )
        bank_mz, _ = BankAccount.objects.get_or_create(
            organization=org,
            account_no="PK12MEZN0000987654301234",
            defaults={
                "name": "JMC Payroll — Meezan",
                "bank_name": "Meezan Bank",
                "currency": "PKR",
                "opening_balance": Decimal("2500000"),
            },
        )

        initiator = users.get("initiator1")
        approver = users.get("approver1")

        # Journals with balanced lines (draft / submitted / approved / posted)
        journal_specs = [
            ("JE-DEMO-001", "submitted", "Site materials purchase — pending LoA", "5100", "1010", "450000", "HO"),
            ("JE-DEMO-002", "submitted", "Professional fees — Skyline", "5500", "1010", "175000", "ADMIN"),
            ("JE-DEMO-003", "draft", "Draft utility accrual", "5300", "2200", "85000", "HO"),
            ("JE-DEMO-004", "approved", "Approved travel reimbursement", "5400", "1010", "42000", "SITE-ISB"),
            ("JE-DEMO-005", "posted", "Posted bank charges", "5700", "1010", "2500", "HO"),
            ("JE-DEMO-006", "submitted", "Subcontractor bill — Lahore site", "5200", "2000", "980000", "SITE-LHR"),
            ("JE-DEMO-007", "posted", "Contract revenue recognition", "1100", "4000", "1500000", "SITE-KHI"),
            ("JE-DEMO-008", "submitted", "Office supplies", "5800", "1010", "28500", "ADMIN"),
        ]
        for ref, status, narr, debit_code, credit_code, amt, cc_code in journal_specs:
            je, created = JournalEntry.objects.get_or_create(
                organization=org,
                reference=ref,
                defaults={
                    "entry_date": today - timedelta(days=hash(ref) % 20),
                    "narration": narr,
                    "status": status,
                    "submitted_by": initiator if status != "draft" else None,
                    "approved_by": approver if status in ("approved", "posted") else None,
                    "posted_at": timezone.now() if status == "posted" else None,
                },
            )
            if created or not je.lines.exists():
                amount = Decimal(amt)
                JournalLine.objects.get_or_create(
                    journal=je,
                    account=accounts[debit_code],
                    defaults={
                        "cost_center": centers.get(cc_code),
                        "debit": amount,
                        "credit": Decimal("0"),
                        "description": narr[:120],
                    },
                )
                JournalLine.objects.get_or_create(
                    journal=je,
                    account=accounts[credit_code],
                    defaults={
                        "cost_center": centers.get(cc_code),
                        "debit": Decimal("0"),
                        "credit": amount,
                        "description": narr[:120],
                    },
                )

        # Vendor invoices mix
        for i, vendor in enumerate(vendors[:8], start=1):
            status = ["draft", "submitted", "submitted", "approved", "paid", "submitted", "draft", "approved"][
                i - 1
            ]
            amt = Decimal(50000 + i * 17500)
            wht = (amt * Decimal("0.10")).quantize(Decimal("0.01"))
            VendorInvoice.objects.get_or_create(
                organization=org,
                vendor=vendor,
                invoice_no=f"INV-2026-{i:04d}",
                defaults={
                    "invoice_date": today - timedelta(days=i * 3),
                    "due_date": today + timedelta(days=30 - i),
                    "amount": amt,
                    "wht_amount": wht,
                    "status": status,
                    "description": f"Demo AP invoice for {vendor.name}",
                },
            )

        for code, name, amount, utilized, status, cc in [
            ("BUD-HO", "HO Operating FY", "8000000", "2100000", "submitted", "HO"),
            ("BUD-LHR", "Lahore Site Capex", "12000000", "4500000", "approved", "SITE-LHR"),
            ("BUD-KHI", "Karachi Site OpEx", "6500000", "900000", "submitted", "SITE-KHI"),
            ("BUD-HR", "HR Training & Welfare", "1500000", "320000", "draft", "HR"),
            ("BUD-ADM", "Admin & Facilities", "2200000", "780000", "approved", "ADMIN"),
        ]:
            Budget.objects.get_or_create(
                organization=org,
                name=name,
                fiscal_year=year,
                defaults={
                    "cost_center": centers[cc],
                    "amount": Decimal(amount),
                    "utilized": Decimal(utilized),
                    "status": status,
                    "notes": f"Seed budget {code}",
                },
            )

        assets = [
            ("FA-001", "Dell Latitude Laptop", "IT Equipment", "Islamabad HO", "Ali Khan", "250000", "180000"),
            ("FA-002", "Toyota Hilux — Site", "Vehicles", "Lahore Site", "Site Store", "6500000", "5200000"),
            ("FA-003", "Excavator Rental Unit", "Plant", "Karachi Site", "Plant Yard", "12000000", "9800000"),
            ("FA-004", "Conference AV System", "IT Equipment", "Islamabad HO", "Admin", "480000", "360000"),
            ("FA-005", "Office Workstations (12)", "Furniture", "Islamabad HO", "Admin", "960000", "720000"),
            ("FA-006", "Generator 50 KVA", "Plant", "Islamabad Site", "Site Store", "2100000", "1680000"),
            ("FA-007", "Survey Total Station", "Equipment", "Lahore Site", "Survey Team", "875000", "700000"),
            ("FA-008", "Server Rack + UPS", "IT Equipment", "Islamabad HO", "IT", "1100000", "880000"),
            ("FA-009", "Safety Scaffolding Set", "Equipment", "Karachi Site", "HSE", "340000", "272000"),
            ("FA-010", "Pickup Suzuki", "Vehicles", "Islamabad Site", "Logistics", "2800000", "2240000"),
        ]
        for code, name, cat, loc, cust, cost, book in assets:
            FixedAsset.objects.get_or_create(
                organization=org,
                asset_code=code,
                defaults={
                    "name": name,
                    "category": cat,
                    "location": loc,
                    "custodian": cust,
                    "purchase_date": date(year - 1, 6, 15),
                    "purchase_cost": Decimal(cost),
                    "depreciation_rate": Decimal("20"),
                    "book_value": Decimal(book),
                    "status": "active",
                },
            )

        Investment.objects.get_or_create(
            organization=org,
            name="HBL TDR 6M — Working Capital",
            defaults={
                "instrument_type": "TDR",
                "principal": Decimal("3000000"),
                "rate_percent": Decimal("14.50"),
                "start_date": today - timedelta(days=60),
                "maturity_date": today + timedelta(days=120),
                "fund_tag": "WC",
                "status": "active",
            },
        )
        Investment.objects.get_or_create(
            organization=org,
            name="Meezan Term Deposit",
            defaults={
                "instrument_type": "TDR",
                "principal": Decimal("1500000"),
                "rate_percent": Decimal("12.75"),
                "start_date": today - timedelta(days=30),
                "maturity_date": today + timedelta(days=335),
                "fund_tag": "Reserve",
                "status": "active",
            },
        )

        TaxChallan.objects.get_or_create(
            organization=org,
            challan_no=f"WHT-{year}-Q1",
            defaults={
                "tax_type": "wht",
                "period_label": f"Q1 {year}",
                "amount": Decimal("185000"),
                "status": "filed",
                "notes": "Demo WHT challan",
            },
        )
        TaxChallan.objects.get_or_create(
            organization=org,
            challan_no=f"ST-{year}-01",
            defaults={
                "tax_type": "st",
                "period_label": today.strftime("%b %Y"),
                "amount": Decimal("92000"),
                "status": "draft",
                "notes": "Demo sales tax challan",
            },
        )

        recon, _ = BankReconciliation.objects.get_or_create(
            organization=org,
            bank_account=bank_hbl,
            statement_date=today.replace(day=1),
            defaults={
                "statement_balance": Decimal("4875000"),
                "book_balance": Decimal("4862000"),
                "status": "open",
                "notes": "Month-open recon demo",
            },
        )
        for i in range(1, 16):
            BankStatementLine.objects.get_or_create(
                organization=org,
                bank_account=bank_hbl,
                txn_date=today - timedelta(days=i),
                description=f"Demo bank txn #{i}",
                defaults={
                    "amount": Decimal(10000 + i * 3500) * (1 if i % 3 else -1),
                    "matched": i % 4 == 0,
                    "reconciliation": recon if i <= 5 else None,
                },
            )
        for i in range(1, 8):
            BankStatementLine.objects.get_or_create(
                organization=org,
                bank_account=bank_mz,
                txn_date=today - timedelta(days=i * 2),
                description=f"Payroll account txn #{i}",
                defaults={"amount": Decimal(-50000 - i * 1000), "matched": False},
            )

    def _hr(self, org, users, today):
        dept_specs = [
            ("FIN", "Finance"),
            ("HR", "Human Resources"),
            ("OPS", "Operations / Sites"),
            ("PROC", "Procurement"),
            ("IT", "Information Technology"),
            ("HSE", "Health, Safety & Environment"),
            ("ADM", "Administration"),
        ]
        depts = {}
        for code, name in dept_specs:
            d, _ = Department.objects.get_or_create(
                organization=org, code=code, defaults={"name": name}
            )
            depts[code] = d

        desig_specs = [
            ("GM", "General Manager"),
            ("MGR", "Manager"),
            ("AMGR", "Assistant Manager"),
            ("OFF", "Officer"),
            ("ENG", "Site Engineer"),
            ("ACC", "Accountant"),
            ("HRX", "HR Executive"),
            ("CLK", "Clerk"),
            ("SUP", "Supervisor"),
        ]
        desigs = {}
        for code, title in desig_specs:
            d, _ = Designation.objects.get_or_create(
                organization=org, code=code, defaults={"title": title}
            )
            desigs[code] = d

        leave_specs = [
            ("AL", "Annual Leave", "14"),
            ("SL", "Sick Leave", "10"),
            ("CL", "Casual Leave", "10"),
            ("UL", "Unpaid Leave", "0"),
        ]
        leave_types = {}
        for code, name, quota in leave_specs:
            lt, _ = LeaveType.objects.get_or_create(
                organization=org,
                code=code,
                defaults={
                    "name": name,
                    "annual_quota": Decimal(quota),
                    "is_paid": code != "UL",
                },
            )
            leave_types[code] = lt

        for code, name, btype, er, ee in [
            ("EOBI", "EOBI Contribution", "eobi", "500", "0"),
            ("MED", "Group Medical", "medical", "2500", "500"),
            ("PF", "Provident Fund", "pf", "0", "0"),
        ]:
            BenefitPlan.objects.get_or_create(
                organization=org,
                code=code,
                defaults={
                    "name": name,
                    "benefit_type": btype,
                    "employer_share": Decimal(er),
                    "employee_share": Decimal(ee),
                    "is_active": True,
                },
            )

        AttendanceDevice.objects.get_or_create(
            organization=org,
            device_id="ZK-HO-01",
            defaults={
                "make": "ZKTeco",
                "model_name": "K40",
                "location": "Islamabad HO Gate",
                "is_active": True,
                "last_sync_at": timezone.now(),
            },
        )
        AttendanceDevice.objects.get_or_create(
            organization=org,
            device_id="ZK-SITE-LHR",
            defaults={
                "make": "ZKTeco",
                "model_name": "iClock",
                "location": "Lahore Site Cabin",
                "is_active": True,
            },
        )

        staff = [
            ("EMP-001", "Ali", "Khan", "ali.khan@jmc.local", "FIN", "ACC", "150000", "ess.user"),
            ("EMP-002", "Ayesha", "Malik", "ayesha.malik@jmc.local", "FIN", "MGR", "220000", "fin.mgr"),
            ("EMP-003", "Bilal", "Ahmed", "bilal.ahmed@jmc.local", "HR", "MGR", "200000", "hr.mgr"),
            ("EMP-004", "Sana", "Qureshi", "sana.qureshi@jmc.local", "FIN", "OFF", "120000", "pay.officer"),
            ("EMP-005", "Imran", "Sheikh", "imran.sheikh@jmc.local", "OPS", "GM", "350000", "approver1"),
            ("EMP-006", "Nadia", "Raza", "nadia.raza@jmc.local", "PROC", "AMGR", "140000", "initiator1"),
            ("EMP-007", "Hassan", "Ali", "hassan.ali@jmc.local", "OPS", "ENG", "135000", None),
            ("EMP-008", "Fatima", "Noor", "fatima.noor@jmc.local", "HR", "HRX", "95000", None),
            ("EMP-009", "Usman", "Tariq", "usman.tariq@jmc.local", "OPS", "SUP", "85000", None),
            ("EMP-010", "Zainab", "Iqbal", "zainab.iqbal@jmc.local", "IT", "OFF", "110000", None),
            ("EMP-011", "Kamran", "Javed", "kamran.javed@jmc.local", "HSE", "OFF", "100000", None),
            ("EMP-012", "Maryam", "Saeed", "maryam.saeed@jmc.local", "ADM", "CLK", "65000", None),
            ("EMP-013", "Tariq", "Mehmood", "tariq.mehmood@jmc.local", "OPS", "ENG", "130000", None),
            ("EMP-014", "Hina", "Bashir", "hina.bashir@jmc.local", "FIN", "ACC", "105000", None),
            ("EMP-015", "Asad", "Farooq", "asad.farooq@jmc.local", "PROC", "OFF", "90000", None),
        ]
        employees = []
        for code, first, last, email, dept, desig, salary, uname in staff:
            linked = users.get(uname) if uname else None
            emp, _ = Employee.objects.update_or_create(
                organization=org,
                employee_code=code,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "email": email,
                    "phone": f"0301{code[-3:]}0000",
                    "department": depts[dept],
                    "designation": desigs[desig],
                    "date_of_joining": date(2023, 1, 15)
                    if code == "EMP-001"
                    else date(2024, (hash(code) % 11) + 1, 10),
                    "status": "active",
                    "basic_salary": Decimal(salary),
                    "user": linked,
                },
            )
            employees.append(emp)

        eobi = BenefitPlan.objects.filter(organization=org, code="EOBI").first()
        med = BenefitPlan.objects.filter(organization=org, code="MED").first()
        for emp in employees:
            if eobi:
                EmployeeBenefit.objects.get_or_create(
                    organization=org,
                    employee=emp,
                    plan=eobi,
                    defaults={"start_date": emp.date_of_joining or today, "status": "active"},
                )
            if med and emp.employee_code <= "EMP-008":
                EmployeeBenefit.objects.get_or_create(
                    organization=org,
                    employee=emp,
                    plan=med,
                    defaults={"start_date": emp.date_of_joining or today, "status": "active"},
                )

        # Attendance last 14 working-ish days for first 10 employees
        for emp in employees[:10]:
            for d in range(14):
                work = today - timedelta(days=d)
                if work.weekday() >= 5:
                    continue
                status = "present"
                if d == 3 and emp.employee_code == "EMP-007":
                    status = "late"
                elif d == 5 and emp.employee_code == "EMP-009":
                    status = "absent"
                AttendanceRecord.objects.get_or_create(
                    organization=org,
                    employee=emp,
                    work_date=work,
                    defaults={
                        "status": status,
                        "check_in": time(9, 0) if status == "present" else None,
                        "check_out": time(17, 30) if status == "present" else None,
                        "notes": "Demo attendance",
                    },
                )

        # Leave requests for LoA inbox
        LeaveRequest.objects.get_or_create(
            employee=employees[0],
            leave_type=leave_types["AL"],
            start_date=today + timedelta(days=7),
            end_date=today + timedelta(days=8),
            defaults={"days": Decimal("2"), "reason": "Family event", "status": "pending"},
        )
        LeaveRequest.objects.get_or_create(
            employee=employees[6],
            leave_type=leave_types["SL"],
            start_date=today - timedelta(days=2),
            end_date=today - timedelta(days=1),
            defaults={"days": Decimal("2"), "reason": "Flu", "status": "approved"},
        )
        LeaveRequest.objects.get_or_create(
            employee=employees[8],
            leave_type=leave_types["CL"],
            start_date=today + timedelta(days=14),
            end_date=today + timedelta(days=14),
            defaults={"days": Decimal("1"), "reason": "Personal", "status": "pending"},
        )
        LeaveRequest.objects.get_or_create(
            employee=employees[2],
            leave_type=leave_types["AL"],
            start_date=today + timedelta(days=21),
            end_date=today + timedelta(days=25),
            defaults={"days": Decimal("5"), "reason": "Annual vacation", "status": "pending"},
        )

        RecruitmentRequest.objects.get_or_create(
            organization=org,
            title="Site Engineer — Lahore",
            defaults={
                "department": depts["OPS"],
                "designation": desigs["ENG"],
                "openings": 2,
                "status": "open",
                "notes": "Urgent for Q2 site ramp-up",
            },
        )
        RecruitmentRequest.objects.get_or_create(
            organization=org,
            title="Accounts Officer",
            defaults={
                "department": depts["FIN"],
                "designation": desigs["ACC"],
                "openings": 1,
                "candidate_name": "Shortlisted — Sara Ali",
                "candidate_email": "sara.ali@candidates.local",
                "status": "interview",
            },
        )
        RecruitmentRequest.objects.get_or_create(
            organization=org,
            title="HSE Supervisor",
            defaults={
                "department": depts["HSE"],
                "designation": desigs["SUP"],
                "openings": 1,
                "status": "open",
            },
        )
        RecruitmentRequest.objects.get_or_create(
            organization=org,
            title="IT Support Officer",
            defaults={
                "department": depts["IT"],
                "designation": desigs["OFF"],
                "openings": 1,
                "status": "offer",
                "candidate_name": "Offer sent — Hamza",
            },
        )

        ProbationRecord.objects.get_or_create(
            organization=org,
            employee=employees[9],
            defaults={
                "start_date": today - timedelta(days=60),
                "end_date": today + timedelta(days=30),
                "status": "on_probation",
                "notes": "IT officer probation",
            },
        )
        PerformanceReview.objects.get_or_create(
            organization=org,
            employee=employees[0],
            period_label=f"H1 {today.year}",
            defaults={
                "rating": Decimal("4.20"),
                "goals": "Improve month-end close cycle",
                "feedback": "Strong ownership",
                "status": "submitted",
            },
        )
        PerformanceReview.objects.get_or_create(
            organization=org,
            employee=employees[6],
            period_label=f"H1 {today.year}",
            defaults={
                "rating": Decimal("3.80"),
                "goals": "Site delivery KPIs",
                "status": "draft",
            },
        )
        TrainingRecord.objects.get_or_create(
            organization=org,
            employee=employees[10],
            title="NEBOSH HSE Awareness",
            defaults={
                "provider": "PIQC",
                "start_date": today + timedelta(days=10),
                "end_date": today + timedelta(days=12),
                "status": "planned",
            },
        )
        TrainingRecord.objects.get_or_create(
            organization=org,
            employee=employees[1],
            title="IFRS for Construction",
            defaults={
                "provider": "ICAP CPD",
                "start_date": today - timedelta(days=40),
                "end_date": today - timedelta(days=38),
                "status": "completed",
            },
        )
        EmployeeDocument.objects.get_or_create(
            organization=org,
            employee=employees[0],
            title="CNIC Copy",
            defaults={
                "doc_type": "identity",
                "reference": "37405-1234567-1",
                "issued_on": date(2020, 1, 1),
                "expires_on": date(2030, 1, 1),
            },
        )
        EmployeeDocument.objects.get_or_create(
            organization=org,
            employee=employees[4],
            title="Employment Contract",
            defaults={"doc_type": "contract", "issued_on": date(2023, 6, 1)},
        )
        # One closed separation (ex-employee style sample on last staff slot clone would be heavy;
        # attach initiated separation demo on EMP-015 instead as initiated only)
        SeparationRecord.objects.get_or_create(
            organization=org,
            employee=employees[14],
            defaults={
                "last_working_day": today + timedelta(days=30),
                "reason": "Resignation — relocation",
                "final_settlement": Decimal("185000"),
                "status": "initiated",
                "notes": "Demo exit workflow",
            },
        )

        return len(depts), len(desigs), Employee.objects.filter(organization=org), len(leave_types)

    def _payroll(self, org, employees_qs, today):
        SalaryStructure.objects.get_or_create(
            organization=org,
            code="STD",
            defaults={
                "name": "Standard Grade",
                "basic": Decimal("100000"),
                "housing": Decimal("25000"),
                "transport": Decimal("10000"),
                "other_allowances": Decimal("5000"),
            },
        )
        SalaryStructure.objects.get_or_create(
            organization=org,
            code="MGR",
            defaults={
                "name": "Manager Grade",
                "basic": Decimal("180000"),
                "housing": Decimal("45000"),
                "transport": Decimal("20000"),
                "other_allowances": Decimal("15000"),
            },
        )
        SalaryStructure.objects.get_or_create(
            organization=org,
            code="SITE",
            defaults={
                "name": "Site Staff Grade",
                "basic": Decimal("80000"),
                "housing": Decimal("15000"),
                "transport": Decimal("12000"),
                "other_allowances": Decimal("8000"),
            },
        )

        # Prior month paid, current processing, next open
        def period_for(y, m, status):
            name = date(y, m, 1).strftime("%B %Y")
            p, _ = PayrollPeriod.objects.get_or_create(
                organization=org,
                year=y,
                month=m,
                defaults={"name": name, "status": status},
            )
            if p.status != status and status == "processing":
                p.status = status
                p.save(update_fields=["status"])
            return p

        cur_y, cur_m = today.year, today.month
        prev = (date(cur_y, cur_m, 1) - timedelta(days=1))
        nxt_m = cur_m + 1
        nxt_y = cur_y
        if nxt_m == 13:
            nxt_m, nxt_y = 1, cur_y + 1

        prior = period_for(prev.year, prev.month, "paid")
        current = period_for(cur_y, cur_m, "processing")
        period_for(nxt_y, nxt_m, "open")

        for period in (prior, current):
            for emp in employees_qs.filter(status="active")[:12]:
                basic = emp.basic_salary or Decimal("100000")
                allowances = (basic * Decimal("0.15")).quantize(Decimal("0.01"))
                deductions = Decimal("2000")
                tax = (basic * Decimal("0.05")).quantize(Decimal("0.01"))
                eobi = Decimal("500")
                net = basic + allowances - deductions - tax - eobi
                Payslip.objects.get_or_create(
                    period=period,
                    employee=emp,
                    defaults={
                        "basic": basic,
                        "allowances": allowances,
                        "deductions": deductions,
                        "tax": tax,
                        "eobi": eobi,
                        "net_pay": net,
                    },
                )

    def _email_profiles(self, org):
        from core.email_defaults import ensure_default_email_templates

        ensure_default_email_templates(org)
        for name, email, purpose, default in [
            ("JMC General", "noreply@jmc.local", "general", True),
            ("JMC HR Desk", "hr@jmc.local", "hr", False),
            ("JMC Finance", "finance@jmc.local", "finance", False),
            ("JMC Payroll", "payroll@jmc.local", "payroll", False),
            ("JMC Workflow", "approvals@jmc.local", "workflow", False),
        ]:
            TenantEmailProfile.objects.get_or_create(
                organization=org,
                email=email,
                defaults={
                    "name": name,
                    "purpose": purpose,
                    "is_default": default,
                    "is_active": True,
                },
            )
