from django.contrib import admin

from hr.models import Department, Designation, Employee, LeaveRequest, LeaveType

admin.site.register(Department)
admin.site.register(Designation)
admin.site.register(Employee)
admin.site.register(LeaveType)
admin.site.register(LeaveRequest)
