#!/bin/bash
# Undo JMC-triggered Traefik ACME fallout. Does not start JMC.
set -euo pipefail

echo "=== ensure JMC is down ==="
cd /home/sidms/jmc
docker compose down 2>/dev/null || true
docker ps -a --filter name=jmc_ --format '{{.Names}} {{.Status}}' || true

echo
echo "=== what JMC added (labels that forced ACME) ==="
echo "jmc used tls.certresolver=cloudflare on web network -> Traefik re-issued certs for ALL routers"
echo "ACME failed -> TRAEFIK DEFAULT CERT for scpms/sidms"

echo
echo "=== Traefik backups ==="
ls -lt /home/sidms/traefik/docker-compose.yml* | head -10

cd /home/sidms/traefik

echo
echo "=== host can reach LE? ==="
curl -sS --max-time 15 -o /tmp/le.json -w 'code=%{http_code}\n' https://acme-v02.api.letsencrypt.org/directory || echo FAIL
head -c 80 /tmp/le.json; echo

echo
echo "=== docker bridge reach LE? ==="
# use traefik image itself for network test
docker run --rm --dns 1.1.1.1 curlimages/curl:8.5.0 -sS --max-time 15 -o /dev/null -w 'curl_img=%{http_code}\n' https://acme-v02.api.letsencrypt.org/directory 2>&1 || \
docker run --rm --network host curlimages/curl:8.5.0 -sS --max-time 15 -o /dev/null -w 'curl_hostnet=%{http_code}\n' https://acme-v02.api.letsencrypt.org/directory 2>&1 || \
echo 'curl image unavailable, try wget on host network traefik recreate'

echo
echo "=== fix Docker DNS permanently (daemon.json) without touching app stacks ==="
if [ -f /etc/docker/daemon.json ]; then
  cp -a /etc/docker/daemon.json /etc/docker/daemon.json.bak.$(date +%Y%m%d%H%M%S)
  cat /etc/docker/daemon.json
else
  echo '{}' | sudo tee /etc/docker/daemon.json >/dev/null
fi

# merge dns into daemon.json
python3 <<'PY'
import json
from pathlib import Path
p=Path('/etc/docker/daemon.json')
try:
  d=json.loads(p.read_text() or '{}')
except Exception:
  d={}
d['dns']=['1.1.1.1','8.8.8.8']
# write via stdout for sudo tee
print(json.dumps(d, indent=2))
PY
# need sudo write
python3 <<'PY' | sudo tee /etc/docker/daemon.json >/dev/null
import json
from pathlib import Path
p=Path('/etc/docker/daemon.json')
try:
  d=json.loads(p.read_text() or '{}')
except Exception:
  d={}
d['dns']=['1.1.1.1','8.8.8.8']
print(json.dumps(d, indent=2))
PY
echo "daemon.json now:"; cat /etc/docker/daemon.json

echo
echo "NOTE: restarting docker would bounce ALL containers — skip full docker restart."
echo "Instead recreate ONLY traefik on host network for ACME + publish 80/443."

# Prefer host network so Traefik uses host DNS/routing to reach LE, still uses docker provider via socket.
# Apps keep their labels; brief HTTPS blip only for Traefik recreate.

LE_IP=$(getent ahostsv4 acme-v02.api.letsencrypt.org | awk '{print $1; exit}')
echo "LE_IP=$LE_IP"

cp -a docker-compose.yml docker-compose.yml.pre_hostnet.$(date +%Y%m%d%H%M%S)

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

# Fix YAML escaping - rewrite cleanly without backslash issues
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

# inject extra_hosts with real IP
if [ -n "$LE_IP" ]; then
  python3 - <<PY
from pathlib import Path
p=Path('docker-compose.yml')
t=p.read_text()
block="    extra_hosts:\n      - \"acme-v02.api.letsencrypt.org:$LE_IP\"\n"
t=t.replace("    env_file:\n", block+"    env_file:\n", 1)
p.write_text(t)
print('extra_hosts set')
PY
fi

echo "=== recreate traefik (host network) ==="
docker compose up -d --force-recreate traefik
sleep 5
docker ps --filter name=^traefik$ --format '{{.Names}} {{.Status}}'

echo "=== LE from traefik ==="
curl -sS --max-time 15 -o /dev/null -w 'hostcurl=%{http_code}\n' https://acme-v02.api.letsencrypt.org/directory || true
# in host network, traefik shares host stack — test via docker exec curl if exists
docker exec traefik wget -qO- --timeout=15 https://acme-v02.api.letsencrypt.org/directory 2>&1 | head -c 200 || true
echo

sleep 10
echo "=== ACME / certs ==="
docker logs traefik --since 45s 2>&1 | grep -iE 'acme|certificate|ERR|error|Obtain' | tail -40 || true
echo | openssl s_client -connect 127.0.0.1:443 -servername scpms-app.sidms.online 2>/dev/null | openssl x509 -noout -subject -issuer -dates 2>/dev/null || true
python3 - <<'PY'
import json
d=json.load(open('/home/sidms/traefik/acme.json'))
certs=d.get('cloudflare',{}).get('Certificates')
print('stored certs', 0 if certs is None else len(certs))
if certs:
  for c in certs:
    print(' ', c.get('domain'))
PY

echo
echo "=== local through traefik ==="
curl -k -sS -o /dev/null -w 'scpms/login %{http_code}\n' --max-time 10 --resolve scpms-app.sidms.online:443:127.0.0.1 https://scpms-app.sidms.online/login
curl -k -sS -o /dev/null -w 'sidms/ %{http_code}\n' --max-time 10 --resolve sidms.sidms.online:443:127.0.0.1 https://sidms.sidms.online/
curl -sS --max-time 5 http://127.0.0.1:8080/api/http/routers 2>/dev/null | python3 -c 'import sys,json; d=json.load(sys.stdin);
print("routers", len(d));
[print(r["name"], r.get("status")) for r in d if "@docker" in r.get("name","")]' 2>/dev/null || \
curl -sS --max-time 5 http://127.0.0.1:9080/api/http/routers 2>/dev/null | python3 -c 'import sys,json; d=json.load(sys.stdin);
print("routers9080", len(d));
[print(r["name"], r.get("status")) for r in d if "@docker" in r.get("name","")]' 2>/dev/null || true

echo
echo "=== public DNS reminder ==="
python3 - <<'PY'
import socket
print('scpms-app resolves', sorted({a[4][0] for a in socket.getaddrinfo('scpms-app.sidms.online',443,socket.AF_INET)}))
print('If NS is lander.d.parity.domains, Cloudflare dashboard records are NOT used publicly.')
print('Registrar must use Cloudflare nameservers for CF DNS to control the domain.')
PY
