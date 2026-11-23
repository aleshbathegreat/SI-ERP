#!/bin/bash
set -euo pipefail
cd /home/sidms/traefik
LE=$(getent ahostsv4 acme-v02.api.letsencrypt.org | awk '{print $1; exit}')
echo "LE=$LE"
if [ -n "$LE" ]; then
  sed -i "s/172.65.32.248/${LE}/" docker-compose.yml || true
fi
touch acme.json
chmod 600 acme.json
sudo ufw allow 80/tcp >/dev/null 2>&1 || true
sudo ufw allow 443/tcp >/dev/null 2>&1 || true
docker compose up -d --force-recreate traefik
sleep 5
docker ps --filter name=^traefik$ --format '{{.Names}} {{.Status}}'
curl -k -sS -o /dev/null -w 'scpms/login=%{http_code}\n' --max-time 8 --resolve scpms-app.sidms.online:443:127.0.0.1 https://scpms-app.sidms.online/login
curl -k -sS -o /dev/null -w 'sidms=%{http_code}\n' --max-time 8 --resolve sidms.sidms.online:443:127.0.0.1 https://sidms.sidms.online/
echo | openssl s_client -connect 127.0.0.1:443 -servername scpms-app.sidms.online 2>/dev/null | openssl x509 -noout -subject -issuer 2>/dev/null || true
echo "=== latest ACME ==="
docker logs traefik --since 45s 2>&1 | grep -iE 'acme|certificate|ERR' | tail -12 || true
echo "=== DNS still ==="
python3 - <<'PY'
import socket
ORIGIN='82.38.44.122'
for h in ['scpms-app.sidms.online','sidms.sidms.online']:
  ips=sorted({a[4][0] for a in socket.getaddrinfo(h,443,socket.AF_INET)})
  print(h, ips, 'OK' if ips==[ORIGIN] else 'NEED Namecheap A -> '+ORIGIN)
PY
echo "=== namecheap creds on disk? ==="
grep -rIl --include='*.env' --include='.env*' -iE 'NAMECHEAP|ApiKey' /home/sidms --exclude-dir=.cursor-server --exclude-dir=.npm --exclude-dir=.cache 2>/dev/null | head -20 || true
