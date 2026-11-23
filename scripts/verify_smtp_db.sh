#!/bin/bash
docker exec jmc_api python manage.py shell <<'PY'
from core.models import TenantSmtpSettings, TenantEmailProfile, Organization
o = Organization.objects.first()
s = TenantSmtpSettings.objects.get(organization=o)
print("org", o.code)
print("smtp", s.host, s.port, s.from_email, "active=", s.is_active, "pwd_set=", bool(s.password), "tls=", s.use_tls)
print("profiles", list(TenantEmailProfile.objects.filter(organization=o).values_list("purpose", "email", "is_active")))
PY
