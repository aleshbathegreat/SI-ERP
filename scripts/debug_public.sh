#!/bin/bash
cd /home/sidms/jmc || exit 1

echo "=== containers ==="
docker compose ps

echo "=== DNS local ==="
getent hosts si-erp.sidms.online si-erp-api.sidms.online || true
echo "server public ip:"
curl -4 -sS ifconfig.me || curl -4 -sS icanhazip.com || true
echo

echo "=== listening ==="
ss -lntp | grep -E ':80|:443' || netstat -lntp 2>/dev/null | grep -E ':80|:443' || true

echo "=== traefik containers ==="
docker ps --format '{{.Names}} {{.Status}}' | grep -i traefik

echo "=== jmc on web network ==="
docker network inspect web --format '{{range .Containers}}{{.Name}} {{end}}' | tr ' ' '\n' | grep -E 'jmc|traefik' || true

echo "=== labels ==="
docker inspect jmc_web --format '{{json .Config.Labels}}' | python3 -c "import sys,json; d=json.load(sys.stdin); print('\n'.join(f'{k}={v}' for k,v in sorted(d.items()) if 'traefik' in k))"
docker inspect jmc_api --format '{{json .Config.Labels}}' | python3 -c "import sys,json; d=json.load(sys.stdin); print('\n'.join(f'{k}={v}' for k,v in sorted(d.items()) if 'traefik' in k))"

echo "=== local https via resolve ==="
curl -k -sS -o /dev/null -w "web:%{http_code} time:%{time_total}\n" --resolve si-erp.sidms.online:443:127.0.0.1 https://si-erp.sidms.online/login
curl -k -sS -o /dev/null -w "api:%{http_code} time:%{time_total}\n" --resolve si-erp-api.sidms.online:443:127.0.0.1 https://si-erp-api.sidms.online/api/health/

echo "=== public https (as internet sees) ==="
curl -sS -o /dev/null -w "web_pub:%{http_code} err:%{errormsg}\n" --connect-timeout 10 https://si-erp.sidms.online/login || true
curl -sS -o /dev/null -w "api_pub:%{http_code} err:%{errormsg}\n" --connect-timeout 10 https://si-erp-api.sidms.online/api/health/ || true

echo "=== compare working scpms ==="
curl -sS -o /dev/null -w "scpms_pub:%{http_code}\n" --connect-timeout 10 https://scpms-app.sidms.online/ || true
getent hosts scpms-app.sidms.online || true

echo "=== recent traefik cert errors for jmc ==="
docker logs traefik 2>&1 | grep -i 'si-erp\|jmc' | tail -20
