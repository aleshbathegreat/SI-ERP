#!/bin/bash
set -e
echo "=== traefik dir ==="
ls -la /home/sidms/traefik
echo "=== compose ==="
sed -n '1,200p' /home/sidms/traefik/docker-compose.yml 2>/dev/null || sed -n '1,200p' /home/sidms/traefik/compose.yml

echo "=== DNS compare ==="
for h in si-erp.sidms.online si-erp-api.sidms.online scpms-app.sidms.online sipulse-frontend.sidms.online sipulse-api.sidms.online; do
  echo -n "$h -> "
  dig +short "$h" A 2>/dev/null || getent ahostsv4 "$h" | awk '{print $1; exit}'
done

echo "=== server ip ==="
curl -4 -sS --max-time 5 ifconfig.me; echo

echo "=== local https working hosts ==="
for h in scpms-app.sidms.online sipulse-frontend.sidms.online si-erp.sidms.online; do
  code=$(curl -k -sS -o /dev/null -w "%{http_code}" --max-time 5 --resolve ${h}:443:127.0.0.1 https://${h}/ 2>/dev/null || echo fail)
  echo "$h local:$code"
done

echo "=== acme domains mentioning si-erp or scpms ==="
ACME=$(find /home/sidms/traefik -name 'acme.json' 2>/dev/null | head -1)
echo "acme=$ACME"
if [ -n "$ACME" ]; then
  python3 - <<PY
import json
p="$ACME"
try:
  d=json.load(open(p))
except Exception as e:
  print("cannot read", e); raise SystemExit
# traefik v2 structure varies
found=[]
def walk(o):
  if isinstance(o, dict):
    for k,v in o.items():
      if k in ("domain","main","sans") and isinstance(v,(str,list)):
        found.append((k,v))
      walk(v)
  elif isinstance(o, list):
    for i in o: walk(i)
walk(d)
text=json.dumps(d)
for needle in ["si-erp","scpms-app","sipulse-frontend","sipulse-api"]:
  print(needle, "YES" if needle in text else "NO")
PY
fi

echo "=== jmc routers present in traefik api? ==="
# try traefik api if exposed
curl -sS --max-time 3 http://127.0.0.1:8080/api/http/routers 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print('\n'.join(r.get('name','')+':'+r.get('status','')+':'+str(r.get('rule')) for r in d if 'jmc' in r.get('name','').lower() or 'si-erp' in str(r.get('rule','')).lower() or 'scpms-app' in r.get('name','').lower())[:30])" 2>/dev/null || echo "no traefik api on 8080"

echo "=== recent jmc traefik lines ==="
docker logs traefik --since 30m 2>&1 | grep -iE 'si-erp|jmc-' | tail -15 || true
