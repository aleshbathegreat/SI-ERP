"""One-shot: set tenant SMTP from env (run inside jmc_api from /app)."""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from core.models import Organization, TenantEmailProfile, TenantSmtpSettings

host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
port = int(os.environ.get("SMTP_PORT", "587"))
user = os.environ["SMTP_USER"]
password = os.environ["SMTP_PASSWORD"].replace(" ", "")
from_name = os.environ.get("SMTP_FROM_NAME", "JMC ERP Payroll")
org_code = os.environ.get("ORG_CODE", "jmc")

org = Organization.objects.filter(code=org_code).first() or Organization.objects.first()
assert org, "no organization"

smtp, _ = TenantSmtpSettings.objects.get_or_create(organization=org)
smtp.host = host
smtp.port = port
smtp.username = user
smtp.password = password
smtp.use_tls = True
smtp.use_ssl = False
smtp.from_email = user
smtp.from_name = from_name
smtp.reply_to = user
smtp.is_active = True
smtp.save()

# unique (organization, email) — one mailbox identity, default + payroll purpose
prof = TenantEmailProfile.objects.filter(organization=org, email=user).first()
if not prof:
    prof = TenantEmailProfile(organization=org, email=user)
prof.name = from_name
prof.purpose = "payroll"
prof.reply_to = user
prof.is_default = True
prof.is_active = True
prof.save()

print(
    "OK",
    org.code,
    smtp.host,
    smtp.from_email,
    "active=",
    smtp.is_active,
    "pwd_set=",
    bool(smtp.password),
    "pwd_len=",
    len(smtp.password),
)
print(
    "profiles",
    list(
        TenantEmailProfile.objects.filter(organization=org).values_list(
            "purpose", "email", "is_default", "is_active"
        )
    ),
)
