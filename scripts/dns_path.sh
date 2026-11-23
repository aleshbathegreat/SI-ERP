#!/bin/bash
set -e
echo "=== server addresses ==="
ip -4 addr show | awk '/inet /{print $2,$NF}'
echo "=== listening 80/443 ==="
ss -lntp | grep -E ':80|:443' || netstat -lntp 2>/dev/null | grep -E ':80|:443'

echo "=== acme Certificates raw ==="
python3 - <<'PY'
import json
d=json.load(open('/home/sidms/traefik/acme.json'))
certs=d.get('cloudflare',{}).get('Certificates')
print(type(certs), certs)
PY

echo "=== traefik routers via file ==="
curl -sS --max-time 5 http://127.0.0.1:9080/api/http/routers > /tmp/tr_routers.json
python3 - <<'PY'
import json
d=json.load(open('/tmp/tr_routers.json'))
for r in d:
  name=r.get('name','')
  rule=str(r.get('rule',''))
  if any(x in name.lower() or x in rule.lower() for x in ['jmc','si-erp','sipulse','scpms']):
    print(f"{name} status={r.get('status')} provider={r.get('provider')} tls={r.get('tls')} rule={rule}")
print('total routers', len(d))
PY

echo "=== container names with traefik enable ==="
docker ps --format '{{.Names}}' | while read n; do
  en=$(docker inspect "$n" --format '{{index .Config.Labels "traefik.enable"}}' 2>/dev/null)
  host=$(docker inspect "$n" --format '{{range $k,$v := .Config.Labels}}{{println $k "=" $v}}{{end}}' 2>/dev/null | grep -i 'rule=' | head -2)
  if [ "$en" = "true" ]; then
    echo "$n"
    echo "$host"
    echo "---"
  fi
done

echo "=== dig from 1.1.1.1 ==="
for h in si-erp.sidms.online si-erp-api.sidms.online sipulse-frontend.sidms.online scpms-app.sidms.online; do
  echo -n "$h @1.1.1.1 -> "
  dig +short "$h" A @1.1.1.1
  echo -n "$h @8.8.8.8 -> "
  dig +short "$h" A @8.8.8.8
done

echo "=== cloudflared / tunnel? ==="
docker ps -a --format '{{.Names}} {{.Image}}' | grep -iE 'cloudflare|tunnel' || true
ps aux | grep -iE 'cloudflared|tunnel' | grep -v grep || true

echo "=== traefik resolve LE ==="
docker exec traefik wget -qO- --timeout=5 https://1.1.1.1 2>&1 | head -3 || true
docker exec traefik cat /etc/resolv.conf
echo "=== host resolve LE ==="
getent hosts acme-v02.api.letsencrypt.org || dig +short acme-v02.api.letsencrypt.org
