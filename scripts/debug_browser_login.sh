#!/bin/bash
set -euo pipefail
echo "=== frontend env / baked API URL ==="
# Next standalone often embeds NEXT_PUBLIC_* at build time
docker exec jmc_web sh -c 'echo PORT=$PORT; ls /app 2>/dev/null | head; find /app -name "*.env*" 2>/dev/null | head; grep -Rola "si-erp-api\.[a-z.]*\|NEXT_PUBLIC_API_URL\|sidms.online\|mushaz.com" /app/.next 2>/dev/null | head -40' || true
docker exec jmc_web sh -c 'grep -Rola "si-erp-api[^\"]*" /app 2>/dev/null | sort -u | head -30' || true

echo
echo "=== public login page + API from outside CF perspective (server curl may get 1010) ==="
curl -sS -o /tmp/login.html -w "login_page=%{http_code}\n" --max-time 20 https://si-erp.mushaz.com/login || true
grep -oE 'si-erp-api[^\"'\'' ]+|sidms\.online|mushaz\.com|/api/auth/login' /tmp/login.html | sort -u | head -40 || true

echo
echo "=== login via public API with browser-like headers ==="
curl -sS -o /tmp/pub_login.json -w "pub_login=%{http_code}\n" --max-time 25 \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json' \
  -H 'Origin: https://si-erp.mushaz.com' \
  -H 'Referer: https://si-erp.mushaz.com/login' \
  -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36' \
  -X POST https://si-erp-api.mushaz.com/api/auth/login/ \
  -d '{"username":"admin","password":"Admin@123"}' || true
head -c 400 /tmp/pub_login.json; echo

echo
echo "=== login via --resolve origin (same Host) ==="
curl -k -sS -o /tmp/loc_login.json -w "local_login=%{http_code}\n" --max-time 20 \
  --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  -H 'Content-Type: application/json' \
  -H 'Origin: https://si-erp.mushaz.com' \
  -X POST https://si-erp-api.mushaz.com/api/auth/login/ \
  -d '{"username":"admin","password":"Admin@123"}'
head -c 300 /tmp/loc_login.json; echo

echo
echo "=== CORS preflight ==="
curl -k -sS -D - -o /dev/null --max-time 15 \
  --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  -X OPTIONS https://si-erp-api.mushaz.com/api/auth/login/ \
  -H 'Origin: https://si-erp.mushaz.com' \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: content-type' | head -30

echo
echo "=== django allowed hosts / cors from container ==="
docker exec jmc_api python -c "from django.conf import settings; print('ALLOWED', settings.ALLOWED_HOSTS); print('CORS', getattr(settings,'CORS_ALLOWED_ORIGINS',None)); print('CSRF', getattr(settings,'CSRF_TRUSTED_ORIGINS',None)); print('FRONTEND', getattr(settings,'FRONTEND_URL',None))"
