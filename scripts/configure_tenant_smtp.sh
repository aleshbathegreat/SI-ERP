#!/bin/bash
# Configure tenant SMTP in DB (pass secrets via env, never commit them).
# Required env: SMTP_USER SMTP_PASSWORD
# Optional: SMTP_HOST SMTP_PORT SMTP_FROM_NAME ORG_CODE
set -euo pipefail

SMTP_HOST="${SMTP_HOST:-smtp.gmail.com}"
SMTP_PORT="${SMTP_PORT:-587}"
SMTP_USER="${SMTP_USER:?set SMTP_USER}"
SMTP_PASSWORD="${SMTP_PASSWORD:?set SMTP_PASSWORD}"
SMTP_FROM_NAME="${SMTP_FROM_NAME:-JMC ERP Payroll}"
ORG_CODE="${ORG_CODE:-jmc}"

# strip spaces from Gmail app password for storage consistency
SMTP_PASSWORD_CLEAN=$(echo "$SMTP_PASSWORD" | tr -d ' ')

docker exec -e HOST="$SMTP_HOST" -e PORT="$SMTP_PORT" -e USERNAME="$SMTP_USER" \
  -e PASSWORD="$SMTP_PASSWORD_CLEAN" -e FROM_NAME="$SMTP_FROM_NAME" -e ORG_CODE="$ORG_CODE" \
  jmc_api python manage.py shell <<'PY'
import os
from core.models import Organization, TenantSmtpSettings, TenantEmailProfile

org = Organization.objects.filter(code=os.environ["ORG_CODE"]).first() or Organization.objects.first()
assert org, "no organization"
smtp, _ = TenantSmtpSettings.objects.get_or_create(organization=org)
smtp.host = os.environ["HOST"]
smtp.port = int(os.environ["PORT"])
smtp.username = os.environ["USERNAME"]
smtp.password = os.environ["PASSWORD"]
smtp.use_tls = True
smtp.use_ssl = False
smtp.from_email = os.environ["USERNAME"]
smtp.from_name = os.environ["FROM_NAME"]
smtp.reply_to = os.environ["USERNAME"]
smtp.is_active = True
smtp.save()

prof, created = TenantEmailProfile.objects.get_or_create(
    organization=org,
    purpose="payroll",
    defaults={
        "name": "Payroll",
        "email": os.environ["USERNAME"],
        "reply_to": os.environ["USERNAME"],
        "is_default": False,
        "is_active": True,
    },
)
if not created:
    prof.email = os.environ["USERNAME"]
    prof.reply_to = os.environ["USERNAME"]
    prof.is_active = True
    prof.save()

# also ensure a default general profile
TenantEmailProfile.objects.get_or_create(
    organization=org,
    purpose="general",
    defaults={
        "name": org.brand_name or org.name,
        "email": os.environ["USERNAME"],
        "reply_to": os.environ["USERNAME"],
        "is_default": True,
        "is_active": True,
    },
)
print("smtp_saved", org.code, smtp.host, smtp.from_email, "active=", smtp.is_active, "pwd_len=", len(smtp.password))
print("payroll_profile", prof.email)
PY

echo "=== SMTP test (to same mailbox) ==="
TOKEN=$(curl -k -sS --max-time 20 --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"Admin@123"}' \
  https://si-erp-api.mushaz.com/api/auth/login/ | python3 -c 'import sys,json; print(json.load(sys.stdin).get("access",""))')
curl -k -sS -o /tmp/smtp_test.json -w "smtp_test=%{http_code}\n" --max-time 45 \
  --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d "{\"email\":\"$SMTP_USER\",\"purpose\":\"payroll\"}" \
  https://si-erp-api.mushaz.com/api/settings/smtp/
cat /tmp/smtp_test.json; echo
echo DONE
