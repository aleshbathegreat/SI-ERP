from decimal import Decimal

from rest_framework import serializers

from payroll.models import EmployeeLoan, LoanRepayment, PayrollPeriod, Payslip, SalaryStructure

RO = ("organization", "created_at", "updated_at", "created_by", "updated_by")


class SalaryStructureSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalaryStructure
        fields = "__all__"
        read_only_fields = RO


class PayrollPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollPeriod
        fields = "__all__"
        read_only_fields = RO


class PayslipSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    employee_code = serializers.CharField(source="employee.employee_code", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)

    class Meta:
        model = Payslip
        fields = "__all__"
        read_only_fields = (
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "gross_pay",
            "total_deductions",
            "employer_cost",
            "net_pay",
            "allowances",
            "deductions",
        )

    def create(self, validated_data):
        slip = Payslip(**validated_data)
        slip.recompute()
        slip.save()
        return slip

    def update(self, instance, validated_data):
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.recompute()
        instance.save()
        return instance


class LoanRepaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanRepayment
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by")


class EmployeeLoanSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    employee_code = serializers.CharField(source="employee.employee_code", read_only=True)
    guarantor_employee_name = serializers.SerializerMethodField()
    repayments = LoanRepaymentSerializer(many=True, read_only=True)

    class Meta:
        model = EmployeeLoan
        fields = "__all__"
        read_only_fields = RO + ("total_repaid",)

    def get_guarantor_employee_name(self, obj):
        if obj.guarantor_id:
            return obj.guarantor.full_name
        return obj.guarantor_name or ""

    def validate(self, attrs):
        principal = attrs.get("principal", getattr(self.instance, "principal", None))
        tenure = attrs.get("tenure_months", getattr(self.instance, "tenure_months", 12))
        rate = attrs.get("interest_rate", getattr(self.instance, "interest_rate", 0))
        installment = attrs.get("monthly_installment")
        if principal is not None and (not installment or Decimal(installment) <= 0):
            tmp = EmployeeLoan(
                principal=principal,
                tenure_months=tenure or 12,
                interest_rate=rate or 0,
            )
            attrs["monthly_installment"] = tmp.compute_installment()

        guarantor = attrs.get("guarantor", getattr(self.instance, "guarantor", None))
        if guarantor is not None:
            attrs["guarantor_name"] = guarantor.full_name
        return attrs

    def create(self, validated_data):
        from calendar import monthrange
        from datetime import date as date_cls

        from core.access import user_organization
        from core.doc_numbers import ensure_doc_no

        request = self.context.get("request")
        org = user_organization(request.user) if request else None
        if org:
            ensure_doc_no(
                validated_data,
                "loan_number",
                org,
                kind="loan",
                model=EmployeeLoan,
            )
        if not validated_data.get("outstanding_balance"):
            validated_data["outstanding_balance"] = validated_data.get(
                "disbursed_amount"
            ) or validated_data.get("principal", 0)
        if not validated_data.get("disbursed_amount"):
            validated_data["disbursed_amount"] = validated_data.get("principal", 0)
        guarantor = validated_data.get("guarantor")
        if guarantor and not validated_data.get("guarantor_name"):
            validated_data["guarantor_name"] = guarantor.full_name
        # Auto EMI if missing
        if not validated_data.get("monthly_installment") or Decimal(
            str(validated_data.get("monthly_installment") or 0)
        ) <= 0:
            tmp = EmployeeLoan(
                principal=validated_data.get("principal") or 0,
                interest_rate=validated_data.get("interest_rate") or 0,
                tenure_months=validated_data.get("tenure_months") or 12,
            )
            validated_data["monthly_installment"] = tmp.compute_installment()
        # Auto end_date from start + tenure months
        start = validated_data.get("start_date")
        tenure = int(validated_data.get("tenure_months") or 12)
        if start and not validated_data.get("end_date"):
            y = start.year + (start.month - 1 + tenure) // 12
            m = (start.month - 1 + tenure) % 12 + 1
            d = min(start.day, monthrange(y, m)[1])
            validated_data["end_date"] = date_cls(y, m, d)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        guarantor = validated_data.get("guarantor", instance.guarantor)
        if "guarantor" in validated_data:
            validated_data["guarantor_name"] = guarantor.full_name if guarantor else ""
        return super().update(instance, validated_data)
