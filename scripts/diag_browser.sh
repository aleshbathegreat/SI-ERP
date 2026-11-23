#!/bin/bash
set -e
echo "=== containers ==="
docker ps --format 'table {{.Names}}\t{{.Status}}' | sort

echo
echo "=== traefik uptime / restarts ==="
docker inspect traefik --format 'status={{.State.Status}} started={{.State.StartedAt}} restarts={{.RestartCount}}'

echo
echo "=== traefik files unchanged? ==="
ls -la /home/sidms/traefik/
md5sum /home/sidms/traefik/docker-compose.yml /home/sidms/traefik/acme.json 2>/dev/null || true

echo
echo "=== routers ==="
curl -sS --max-time 5 http://127.0.0.1:9080/api/http/routers -o /tmp/tr.json
python3 <<'PY'
import json
d=json.load(open('/tmp/tr.json'))
for r in sorted(d, key=lambda x: x.get('name','')):
  if '@docker' in r.get('name',''):
    print(r['name'], r.get('status'), r.get('rule'))
PY

echo
echo "=== local HTTPS ==="
while IFS='|' read -r h p; do
  code=$(curl -k -sS -o /dev/null -w "%{http_code}" --max-time 8 --resolve "${h}:443:127.0.0.1" "https://${h}${p}" || echo fail)
  echo "local ${h}${p} -> ${code}"
done <<'EOF'
scpms-app.sidms.online|/
scpms-api.sidms.online|/admin/
sidms.online|/
sidms.sidms.online|/
office.sidms.online|/
EOF

echo
echo "=== public HTTPS from server (may hairpin) ==="
for h in scpms-app.sidms.online sidms.sidms.online sidms.online; do
  out=$(curl -sS -o /dev/null -w "%{http_code} err=%{errormsg}" --max-time 12 "https://${h}/" 2>&1 || true)
  echo "public $h -> $out"
done

echo
echo "=== DNS A ==="
python3 <<'PY'
import socket
for h in ['scpms-app.sidms.online','sidms.sidms.online','sidms.online','si-erp.sidms.online']:
  try:
    ips=sorted({ai[4][0] for ai in socket.getaddrinfo(h,443,socket.AF_INET)})
  except Exception as e:
    ips=str(e)
  print(h, ips)
print('server', socket.gethostbyname(socket.gethostname()))
PY
ip -4 addr show ens1 | awk '/inet /{print "ens1",$2}'

echo
echo "=== ufw 80/443 ==="
sudo ufw status | grep -E '80|443|Status' || true

echo
echo "=== traefik recent errors ==="
docker logs traefik --since 2h 2>&1 | grep -iE 'ERR|error|acme|fatal' | tail -25 || true

echo
echo "=== web network members ==="
docker network inspect web --format '{{range .Containers}}{{.Name}} {{end}}'
