#!/bin/bash
# Read-only: do not restart or recreate anything.
set -e
echo "=== all containers ==="
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | sort

echo
echo "=== non-jmc traefik apps local HTTPS (must stay 200/3xx) ==="
for h in scpms-app.sidms.online scpms-api.sidms.online; do
  code=$(curl -k -sS -o /dev/null -w "%{http_code}" --max-time 8 --resolve ${h}:443:127.0.0.1 "https://${h}/" 2>/dev/null || echo fail)
  echo "$h -> $code"
done

echo
echo "=== jmc local HTTPS ==="
for h in si-erp.sidms.online si-erp-api.sidms.online; do
  code=$(curl -k -sS -o /dev/null -w "%{http_code}" --max-time 8 --resolve ${h}:443:127.0.0.1 "https://${h}/" 2>/dev/null || echo fail)
  echo "$h -> $code"
done
# api health path
code=$(curl -k -sS -o /dev/null -w "%{http_code}" --max-time 8 --resolve si-erp-api.sidms.online:443:127.0.0.1 "https://si-erp-api.sidms.online/api/health/" 2>/dev/null || echo fail)
echo "si-erp-api /api/health/ -> $code"

echo
echo "=== jmc containers only ==="
docker ps --filter name=jmc_ --format 'table {{.Names}}\t{{.Status}}'

echo
echo "=== traefik container (not restarted) ==="
docker ps --filter name=^traefik$ --format 'table {{.Names}}\t{{.Status}}'

echo
echo "=== routers jmc vs scpms (api) ==="
curl -sS --max-time 5 http://127.0.0.1:9080/api/http/routers > /tmp/tr.json
python3 - <<'PY'
import json
d=json.load(open('/tmp/tr.json'))
for r in sorted(d, key=lambda x: x.get('name','')):
  n=r.get('name','')
  if 'jmc' in n or 'scpms' in n:
    print(n, r.get('status'), r.get('rule'))
PY
