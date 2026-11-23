#!/bin/bash
set -euo pipefail
cd /home/sidms/traefik

# JMC already down; restore Traefik so ACME can reach LE via host network.
# Keep resolver name "cloudflare" to match existing app labels.

LE_IP=$(getent ahostsv4 acme-v02.api.letsencrypt.org | awk '{print $1; exit}')
echo "LE_IP=$LE_IP"

cp -a docker-compose.yml "docker-compose.yml.bak.$(date +%Y%m%d%H%M%S)"

cat > docker-compose.yml <<YAML
services:
  traefik:
    image: traefik:latest
    container_name: traefik
    restart: unless-stopped
    mem_limit: 256m
    memswap_limit: 256m
    network_mode: host
    env_file:
      - path: .env
        required: false
    extra_hosts:
      - "acme-v02.api.letsencrypt.org:${LE_IP}"
    command:
      - "--api.insecure=true"
      - "--api.dashboard=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--providers.docker.network=web"
      - "--entryPoints.web.address=:80"
      - "--entryPoints.web.http.redirections.entryPoint.to=websecure"
      - "--entryPoints.web.http.redirections.entryPoint.scheme=https"
      - "--entryPoints.web.http.redirections.entryPoint.permanent=true"
      - "--entryPoints.websecure.address=:443"
      - "--certificatesresolvers.cloudflare.acme.httpchallenge=true"
      - "--certificatesresolvers.cloudflare.acme.httpchallenge.entrypoint=web"
      - "--certificatesresolvers.cloudflare.acme.email=\${CF_API_EMAIL:-admin@zeeshad.com}"
      - "--certificatesresolvers.cloudflare.acme.storage=/acme.json"
    environment:
      - CF_API_EMAIL=\${CF_API_EMAIL}
      - CF_DNS_API_TOKEN=\${CF_DNS_API_TOKEN}
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
      - "./acme.json:/acme.json"
YAML

# rewrite without shell escape mess
cat > docker-compose.yml <<'YAML'
services:
  traefik:
    image: traefik:latest
    container_name: traefik
    restart: unless-stopped
    mem_limit: 256m
    memswap_limit: 256m
    network_mode: host
    env_file:
      - path: .env
        required: false
    command:
      - "--api.insecure=true"
      - "--api.dashboard=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--providers.docker.network=web"
      - "--entryPoints.web.address=:80"
      - "--entryPoints.web.http.redirections.entryPoint.to=websecure"
      - "--entryPoints.web.http.redirections.entryPoint.scheme=https"
      - "--entryPoints.web.http.redirections.entryPoint.permanent=true"
      - "--entryPoints.websecure.address=:443"
      - "--certificatesresolvers.cloudflare.acme.httpchallenge=true"
      - "--certificatesresolvers.cloudflare.acme.httpchallenge.entrypoint=web"
      - "--certificatesresolvers.cloudflare.acme.email=${CF_API_EMAIL:-admin@zeeshad.com}"
      - "--certificatesresolvers.cloudflare.acme.storage=/acme.json"
    environment:
      - CF_API_EMAIL=${CF_API_EMAIL}
      - CF_DNS_API_TOKEN=${CF_DNS_API_TOKEN}
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
      - "./acme.json:/acme.json"
YAML

if [ -n "${LE_IP}" ]; then
  python3 - <<PY
from pathlib import Path
p=Path('docker-compose.yml')
t=p.read_text()
block='    extra_hosts:\n      - "acme-v02.api.letsencrypt.org:%s"\n' % "$LE_IP"
if 'extra_hosts' not in t:
  t=t.replace('    env_file:\n', block+'    env_file:\n', 1)
  p.write_text(t)
print('compose ready')
print(p.read_text())
PY
fi

docker compose up -d --force-recreate traefik
sleep 6
docker ps --filter name=^traefik$ --format '{{.Names}} {{.Status}}'

echo "=== LE via traefik (host net) ==="
docker exec traefik wget -qO- --timeout=15 https://acme-v02.api.letsencrypt.org/directory 2>&1 | head -c 220 || true
echo

sleep 12
echo "=== logs ==="
docker logs traefik --since 40s 2>&1 | grep -iE 'acme|certificate|ERR|error|Obtain|HTTP challenge' | tail -50 || true

echo "=== cert ==="
echo | openssl s_client -connect 127.0.0.1:443 -servername scpms-app.sidms.online 2>/dev/null | openssl x509 -noout -subject -issuer -dates 2>/dev/null || true

echo "=== local apps ==="
curl -k -sS -o /dev/null -w 'scpms/login %{http_code}\n' --max-time 10 --resolve scpms-app.sidms.online:443:127.0.0.1 https://scpms-app.sidms.online/login
curl -k -sS -o /dev/null -w 'sidms/ %{http_code}\n' --max-time 10 --resolve sidms.sidms.online:443:127.0.0.1 https://sidms.sidms.online/

# dashboard on host network uses 8080 not 9080
curl -sS --max-time 5 http://127.0.0.1:8080/api/http/routers | python3 -c 'import sys,json;d=json.load(sys.stdin);print("routers",len(d));
[print(r["name"],r.get("status"),r.get("rule")) for r in d if "@docker" in r["name"]]' || true

echo
echo "=== PUBLIC NS (Cloudflare dashboard ignored if this is not *.ns.cloudflare.com) ==="
nslookup -type=NS sidms.online 1.1.1.1 2>/dev/null || getent hosts ns1.lander.d.parity.domains || true
python3 - <<'PY'
import socket
print('scpms-app A', sorted({a[4][0] for a in socket.getaddrinfo('scpms-app.sidms.online',443,socket.AF_INET)}))
print('origin should be 82.38.44.122')
PY
