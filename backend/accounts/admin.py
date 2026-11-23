from django.contrib import admin

from accounts.models import Role, UserProfile, UserRole

admin.site.register(UserProfile)
admin.site.register(Role)
admin.site.register(UserRole)
