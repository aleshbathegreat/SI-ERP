#!/bin/bash
set -e
echo "=== scpms containers ==="
docker ps --filter name=scpms --format 'table {{.Names}}\t{{.Status}}'

echo
echo "=== labels ==="
docker inspect scpms-frontend-1 --format '{{range $k,$v := .Config.Labels}}{{println $k "=" $v}}{{end}}' | grep traefik

echo
echo "=== local via traefik ==="
for path in / /login /login/; do
  code=$(curl -k -sS -o /tmp/scpms_body -w "%{http_code}" --max-time 10 --resolve scpms-app.sidms.online:443:127.0.0.1 "https://scpms-app.sidms.online${path}")
  ctype=$(grep -i '^content-type:' /tmp/scpms_hdr 2>/dev/null || true)
  echo -n "local ${path} -> ${code} "
  echo | openssl s_client -connect 127.0.0.1:443 -servername scpms-app.sidms.online 2>/dev/null | openssl x509 -noout -subject 2>/dev/null | head -1
  head -c 200 /tmp/scpms_body; echo; echo
done

# headers for /login
curl -k -sS -D - -o /tmp/scpms_login_body --max-time 10 --resolve scpms-app.sidms.online:443:127.0.0.1 "https://scpms-app.sidms.online/login" | head -30
echo "body_len=$(wc -c </tmp/scpms_login_body)"
head -c 300 /tmp/scpms_login_body; echo

echo
echo "=== direct to frontend container IP ==="
cip=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' scpms-frontend-1 | awk '{print $1}')
echo "frontend_ip=$cip"
curl -sS -o /dev/null -w "direct_login:%{http_code}\n" --max-time 8 "http://${cip}:3000/login" || true
curl -sS -o /dev/null -w "direct_root:%{http_code}\n" --max-time 8 "http://${cip}:3000/" || true

echo
echo "=== frontend logs ==="
docker logs scpms-frontend-1 --since 30m 2>&1 | tail -20

echo
echo "=== DNS from server ==="
python3 - <<'PY'
import socket
print(sorted({ai[4][0] for ai in socket.getaddrinfo('scpms-app.sidms.online',443,socket.AF_INET)}))
PY
