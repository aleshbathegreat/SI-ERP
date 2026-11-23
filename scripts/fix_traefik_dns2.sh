#!/bin/bash
set -euo pipefail
cd /home/sidms/traefik

echo "=== host resolve LE ==="
getent ahostsv4 acme-v02.api.letsencrypt.org | head -5 || true
LE_IP=$(getent ahostsv4 acme-v02.api.letsencrypt.org | awk '{print $1; exit}')
echo "LE_IP=$LE_IP"
if [ -z "${LE_IP:-}" ]; then
  # fallback resolve via python
  LE_IP=$(python3 - <<'PY'
import socket
print(socket.gethostbyname('acme-v02.api.letsencrypt.org'))
PY
)
  echo "LE_IP_py=$LE_IP"
fi

echo "=== traefik resolv.conf ==="
docker exec traefik cat /etc/resolv.conf || true

# Patch compose with extra_hosts for LE + common CF API if needed
python3 <<PY
from pathlib import Path
p=Path('docker-compose.yml')
text=p.read_text()
le="$LE_IP"
block=f"""    extra_hosts:
      - "acme-v02.api.letsencrypt.org:{le}"
      - "acme-staging-v02.api.letsencrypt.org:{le}"
"""
if 'extra_hosts:' in text:
    print('extra_hosts already present')
else:
    text=text.replace('    dns:\n      - 1.1.1.1\n      - 8.8.8.8\n', '    dns:\n      - 1.1.1.1\n      - 8.8.8.8\n'+block)
    p.write_text(text)
    print('patched extra_hosts')
print(p.read_text())
PY

docker compose up -d --force-recreate traefik
sleep 4
echo "=== test LE from traefik ==="
docker exec traefik wget -qO- --timeout=15 https://acme-v02.api.letsencrypt.org/directory 2>&1 | head -c 300 || true
echo

# local apps still ok
for h in scpms-app.sidms.online sidms.sidms.online; do
  code=$(curl -k -sS -o /dev/null -w "%{http_code}" --max-time 10 --resolve ${h}:443:127.0.0.1 "https://${h}/login")
  echo "local $h/login -> $code"
done

echo
echo "=== ACME logs ==="
sleep 8
docker logs traefik --since 1m 2>&1 | grep -iE 'acme|certificate|ERR|error' | tail -40 || true

echo
echo "=== cert now? ==="
echo | openssl s_client -connect 127.0.0.1:443 -servername scpms-app.sidms.online 2>/dev/null | openssl x509 -noout -subject -issuer -dates 2>/dev/null || true
python3 - <<'PY'
import json
d=json.load(open('acme.json'))
print('Certificates', d.get('cloudflare',{}).get('Certificates'))
PY
