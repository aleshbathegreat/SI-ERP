#!/bin/bash
curl -k -sS --max-time 15 --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  https://si-erp-api.mushaz.com/api/public/resolve-host/ > /tmp/brand.json
python3 - <<'PY'
import json
d=json.load(open('/tmp/brand.json'))
print({k:d.get(k) for k in ['brand_name','brand_tagline','brand_logo_url','brand_primary_color']})
PY
