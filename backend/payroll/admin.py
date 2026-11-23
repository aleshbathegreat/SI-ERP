from django.contrib import admin

from payroll.models import PayrollPeriod, Payslip

admin.site.register(PayrollPeriod)
admin.site.register(Payslip)
