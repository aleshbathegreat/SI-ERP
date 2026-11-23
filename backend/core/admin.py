from django.contrib import admin

from core.models import (
    CompanyLink,
    Organization,
    PayFastSettings,
    SubscriptionPackage,
    SubscriptionPayment,
    TenantPayGateway,
)

admin.site.register(Organization)
admin.site.register(SubscriptionPackage)
admin.site.register(SubscriptionPayment)
admin.site.register(CompanyLink)
admin.site.register(PayFastSettings)
admin.site.register(TenantPayGateway)
