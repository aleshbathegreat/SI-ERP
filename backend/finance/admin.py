from django.contrib import admin

from finance.models import Account, CostCenter, JournalEntry, JournalLine, Vendor


class JournalLineInline(admin.TabularInline):
    model = JournalLine
    extra = 1


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "entry_date", "reference", "status", "organization")
    inlines = [JournalLineInline]


admin.site.register(Account)
admin.site.register(CostCenter)
admin.site.register(Vendor)
