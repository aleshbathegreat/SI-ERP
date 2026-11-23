#!/bin/bash
set -euo pipefail
cd /home/sidms/traefik

echo "=== bounce jmc labels to re-trigger ACME for mushaz only ==="
docker compose -f /home/sidms/jmc/docker-compose.yml up -d --force-recreate api web
sleep 15

echo "=== wait for cert ==="
for i in 1 2 3 4 5 6 7 8 9 10; do
  sub=$(echo | openssl s_client -connect 127.0.0.1:443 -servername si-erp.mushaz.com 2>/dev/null | openssl x509 -noout -subject 2>/dev/null || true)
  echo "try $i $sub"
  if echo "$sub" | grep -qi 'si-erp.mushaz.com\|mushaz.com\|Lets Encrypt\|Let.s Encrypt\|R3\|E1\|ISRG'; then
    break
  fi
  sleep 10
done

echo
echo "=== traefik logs mushaz/jmc ==="
docker logs traefik --since 3m 2>&1 | grep -iE 'si-erp|mushaz|jmc-' | tail -30 || true

echo
echo "=== acme.json domains ==="
python3 - <<'PY'
import json
certs=json.load(open('acme.json')).get('cloudflare',{}).get('Certificates') or []
print('count', len(certs))
for c in certs:
  print(c.get('domain'))
PY

echo
echo "=== local ==="
curl -k -sS -o /dev/null -w 'local_web=%{http_code}\n' --max-time 10 --resolve si-erp.mushaz.com:443:127.0.0.1 https://si-erp.mushaz.com/
curl -k -sS -o /dev/null -w 'local_api=%{http_code}\n' --max-time 10 --resolve si-erp-api.mushaz.com:443:127.0.0.1 https://si-erp-api.mushaz.com/api/health/

echo
echo "=== public (via Cloudflare) ==="
curl -sS -o /dev/null -w 'public_web=%{http_code} err=%{errormsg}\n' --max-time 20 https://si-erp.mushaz.com/ || true
curl -sS -o /dev/null -w 'public_api=%{http_code} err=%{errormsg}\n' --max-time 20 https://si-erp-api.mushaz.com/api/health/ || true
curl -sS -o /dev/null -w 'public_web_insecure=%{http_code}\n' -k --max-time 20 https://si-erp.mushaz.com/ || true
