from decimal import Decimal

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payroll", "0002_tor_modules"),
        ("hr", "0004_production_hardening"),
        ("core", "0003_tor_modules"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="salarystructure",
            name="currency",
            field=models.CharField(default="PKR", max_length=3),
        ),
        migrations.AddField(
            model_name="salarystructure",
            name="medical",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
        migrations.AddField(
            model_name="salarystructure",
            name="meal",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
        migrations.AddField(
            model_name="salarystructure",
            name="income_tax_rate",
            field=models.DecimalField(decimal_places=3, default=Decimal("5.000"), max_digits=6),
        ),
        migrations.AddField(
            model_name="salarystructure",
            name="social_security_fixed",
            field=models.DecimalField(decimal_places=2, default=Decimal("500"), max_digits=14),
        ),
        migrations.AddField(
            model_name="salarystructure",
            name="provident_fund_rate",
            field=models.DecimalField(decimal_places=3, default=Decimal("8.330"), max_digits=6),
        ),
        migrations.AddField(
            model_name="salarystructure",
            name="employer_pf_rate",
            field=models.DecimalField(decimal_places=3, default=Decimal("8.330"), max_digits=6),
        ),
        migrations.AlterField(
            model_name="salarystructure",
            name="basic",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
        migrations.AlterField(
            model_name="salarystructure",
            name="housing",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
        migrations.AlterField(
            model_name="salarystructure",
            name="transport",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
        migrations.AlterField(
            model_name="salarystructure",
            name="other_allowances",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
        migrations.AddField(
            model_name="payrollperiod",
            name="pay_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="payrollperiod",
            name="currency",
            field=models.CharField(default="PKR", max_length=3),
        ),
        migrations.AddField(
            model_name="payrollperiod",
            name="notes",
            field=models.TextField(blank=True),
        ),
        # Payslip expansions
        migrations.AddField(model_name="payslip", name="currency", field=models.CharField(default="PKR", max_length=3)),
        migrations.AddField(model_name="payslip", name="housing_allowance", field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name="payslip", name="transport_allowance", field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name="payslip", name="medical_allowance", field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name="payslip", name="meal_allowance", field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name="payslip", name="overtime", field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name="payslip", name="bonus", field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name="payslip", name="commission", field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name="payslip", name="other_earnings", field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name="payslip", name="income_tax", field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name="payslip", name="social_security", field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name="payslip", name="provident_fund", field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name="payslip", name="pension", field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name="payslip", name="loan_repayment", field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name="payslip", name="advance_recovery", field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name="payslip", name="other_deductions", field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name="payslip", name="employer_provident_fund", field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name="payslip", name="employer_social_security", field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name="payslip", name="gross_pay", field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name="payslip", name="total_deductions", field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name="payslip", name="employer_cost", field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(model_name="payslip", name="days_worked", field=models.DecimalField(decimal_places=2, default=Decimal("30"), max_digits=6)),
        migrations.AddField(model_name="payslip", name="unpaid_leave_days", field=models.DecimalField(decimal_places=2, default=0, max_digits=6)),
        migrations.AddField(model_name="payslip", name="overtime_hours", field=models.DecimalField(decimal_places=2, default=0, max_digits=8)),
        migrations.AddField(
            model_name="payslip",
            name="payment_method",
            field=models.CharField(
                choices=[
                    ("bank_transfer", "Bank transfer"),
                    ("cash", "Cash"),
                    ("cheque", "Cheque"),
                    ("wallet", "Mobile wallet"),
                ],
                default="bank_transfer",
                max_length=20,
            ),
        ),
        migrations.AddField(model_name="payslip", name="bank_account", field=models.CharField(blank=True, max_length=64)),
        migrations.AddField(model_name="payslip", name="payment_reference", field=models.CharField(blank=True, max_length=64)),
        migrations.AddField(model_name="payslip", name="payment_date", field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name="payslip", name="remarks", field=models.TextField(blank=True)),
        migrations.AlterField(model_name="payslip", name="basic", field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AlterField(model_name="payslip", name="allowances", field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AlterField(model_name="payslip", name="deductions", field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AlterField(model_name="payslip", name="tax", field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AlterField(model_name="payslip", name="eobi", field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AlterField(model_name="payslip", name="net_pay", field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.CreateModel(
            name="EmployeeLoan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("loan_number", models.CharField(max_length=40)),
                (
                    "loan_type",
                    models.CharField(
                        choices=[
                            ("personal", "Personal"),
                            ("housing", "Housing / mortgage"),
                            ("vehicle", "Vehicle"),
                            ("salary_advance", "Salary advance"),
                            ("education", "Education"),
                            ("medical", "Medical"),
                            ("other", "Other"),
                        ],
                        default="personal",
                        max_length=32,
                    ),
                ),
                ("currency", models.CharField(default="PKR", max_length=3)),
                ("principal", models.DecimalField(decimal_places=2, max_digits=14)),
                ("interest_rate", models.DecimalField(decimal_places=3, default=0, help_text="Annual interest %", max_digits=7)),
                ("tenure_months", models.PositiveIntegerField(default=12)),
                ("monthly_installment", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("disbursed_amount", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("outstanding_balance", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("total_repaid", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("disbursement_date", models.DateField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("pending", "Pending approval"),
                            ("approved", "Approved"),
                            ("active", "Active"),
                            ("closed", "Closed"),
                            ("rejected", "Rejected"),
                            ("written_off", "Written off"),
                        ],
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("purpose", models.TextField(blank=True)),
                ("guarantor_name", models.CharField(blank=True, max_length=120)),
                ("deduct_from_payroll", models.BooleanField(default=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "employee",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="loans",
                        to="hr.employee",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="employee_loans",
                        to="core.organization",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"], "unique_together": {("organization", "loan_number")}},
        ),
        migrations.CreateModel(
            name="LoanRepayment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("due_date", models.DateField(blank=True, null=True)),
                ("paid_date", models.DateField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("paid", "Paid"),
                            ("skipped", "Skipped"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("notes", models.CharField(blank=True, max_length=255)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "loan",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="repayments",
                        to="payroll.employeeloan",
                    ),
                ),
                (
                    "payslip",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="loan_repayments",
                        to="payroll.payslip",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-due_date", "-id"]},
        ),
    ]
