#!/bin/bash
set -euo pipefail
cd /home/sidms/traefik

echo "=== current compose ==="
cat docker-compose.yml

echo
echo "=== env shape (no secrets) ==="
python3 <<'PY'
for line in open('.env'):
    line=line.rstrip('\n')
    if not line or line.lstrip().startswith('#') or '=' not in line:
        continue
    k,v=line.split('=',1)
    v=v.strip().strip('"').strip("'")
    print(k, 'len='+str(len(v)), 'prefix='+repr(v[:6]), 'looks_like_pem_b64='+str(v.startswith('MII')))
PY

echo
echo "=== NS ==="
docker run --rm --network host busybox:1.36 nslookup -type=NS sidms.online 1.1.1.1 2>&1 | tail -20 || true

# Backup compose once
cp -a docker-compose.yml docker-compose.yml.bak.$(date +%Y%m%d%H%M%S)

# Rewrite compose: keep resolver name "cloudflare" so existing labels keep working,
# but use HTTP challenge on entrypoint web (Traefik handles ACME path before redirect),
# and pin public DNS for the Traefik container so LE is reachable.
cat > docker-compose.yml <<'YAML'
# Copy .env.example → .env and set CF_DNS_API_TOKEN (Zone: DNS:Edit for sidms.online).
# chmod 600 acme.json && docker compose up -d

services:
  traefik:
    image: traefik:latest
    container_name: traefik
    restart: unless-stopped
    mem_limit: 256m
    memswap_limit: 256m
    env_file:
      - path: .env
        required: false
    dns:
      - 1.1.1.1
      - 8.8.8.8
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entryPoints.web.address=:80"
      - "--entryPoints.web.http.redirections.entryPoint.to=websecure"
      - "--entryPoints.web.http.redirections.entryPoint.scheme=https"
      - "--entryPoints.web.http.redirections.entryPoint.permanent=true"
      - "--entryPoints.websecure.address=:443"
      # Keep resolver name "cloudflare" to match existing container labels.
      # HTTP-01 works without Cloudflare API; needs public DNS → this server and :80 open.
      - "--certificatesresolvers.cloudflare.acme.httpchallenge=true"
      - "--certificatesresolvers.cloudflare.acme.httpchallenge.entrypoint=web"
      - "--certificatesresolvers.cloudflare.acme.email=${CF_API_EMAIL:-admin@zeeshad.com}"
      - "--certificatesresolvers.cloudflare.acme.storage=/acme.json"
    ports:
      - "80:80"
      - "443:443"
      - "9080:8080"
    environment:
      - CF_API_EMAIL=${CF_API_EMAIL}
      - CF_DNS_API_TOKEN=${CF_DNS_API_TOKEN}
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
      - "./acme.json:/acme.json"
    networks:
      - web

networks:
  web:
    external: true
YAML

echo
echo "=== new compose ==="
cat docker-compose.yml

echo
echo "=== recreate traefik only ==="
docker compose up -d --force-recreate traefik

echo
echo "=== wait / verify ==="
sleep 5
docker ps --filter name=^traefik$ --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
docker exec traefik getent hosts acme-v02.api.letsencrypt.org || docker exec traefik wget -qO- --timeout=8 https://acme-v02.api.letsencrypt.org/directory | head -c 200 || true
echo

# Trigger / verify local routes still work
for h in scpms-app.sidms.online sidms.sidms.online; do
  code=$(curl -k -sS -o /dev/null -w "%{http_code}" --max-time 10 --resolve ${h}:443:127.0.0.1 "https://${h}/")
  echo "local $h -> $code"
  echo | openssl s_client -connect 127.0.0.1:443 -servername "$h" 2>/dev/null | openssl x509 -noout -subject -issuer 2>/dev/null || true
done

echo
echo "=== recent ACME log ==="
docker logs traefik --since 2m 2>&1 | grep -iE 'acme|certificate|error|ERR' | tail -30 || true

echo
echo "=== DNS still wrong for public? ==="
python3 - <<'PY'
import socket
for h in ['scpms-app.sidms.online','sidms.sidms.online']:
  print(h, sorted({ai[4][0] for ai in socket.getaddrinfo(h,443,socket.AF_INET)}))
print('need A -> 82.38.44.122 for HTTP-01 + browsers')
PY
