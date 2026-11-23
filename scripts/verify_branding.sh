#!/bin/bash
set -euo pipefail
docker inspect jmc_api --format 'api={{.State.Health.Status}}'
curl -k -sS --max-time 15 --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"Admin@123"}' \
  https://si-erp-api.mushaz.com/api/auth/login/ > /tmp/login.json
python3 - <<'PY'
import json
d=json.load(open('/tmp/login.json'))
org=d.get('organization') or {}
print('login_ok', bool(d.get('access')))
print('org_brand', {k: org.get(k) for k in ['brand_name','brand_tagline','brand_primary_color','brand_secondary_color','brand_logo_url']})
open('/tmp/tok','w').write(d.get('access',''))
PY
TOKEN=$(cat /tmp/tok)
curl -k -sS --max-time 15 --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  -H "Authorization: Bearer $TOKEN" \
  https://si-erp-api.mushaz.com/api/settings/domain/ > /tmp/domain.json
python3 - <<'PY'
import json
d=json.load(open('/tmp/domain.json'))
print('domain', {k:d.get(k) for k in ['brand_name','brand_tagline','brand_primary_color','brand_secondary_color','brand_logo_url']})
PY
curl -k -sS -o /dev/null -w 'loans=%{http_code}\n' --max-time 10 \
  --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  -H "Authorization: Bearer $TOKEN" \
  https://si-erp-api.mushaz.com/api/payroll/loans/
curl -k -sS -o /dev/null -w 'resolve=%{http_code}\n' --max-time 10 \
  --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  https://si-erp-api.mushaz.com/api/public/resolve-host/
echo DONE
