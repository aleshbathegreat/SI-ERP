#!/bin/bash
# Stabilize Traefik; prepare HTTP-01; detect Namecheap BasicDNS zone; force renew when A→origin.
set -euo pipefail
ORIGIN=82.38.44.122
cd /home/sidms/traefik

echo "======== Query Namecheap NS directly ========"
python3 <<'PY'
import socket,struct,random,sys

def query(server, name, qtype):
    tid=random.randint(0,65535)
    header=struct.pack('!HHHHHH', tid, 0x0100, 1, 0, 0, 0)
    q=b''.join(bytes([len(p)])+p.encode() for p in name.split('.'))+b'\x00'+struct.pack('!HH', qtype, 1)
    s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(8)
    try:
        s.sendto(header+q,(server,53)); data,_=s.recvfrom(4096)
    finally:
        s.close()
    return data

def parse_name(data,i):
    labels=[]; jumped=False; end=i
    while True:
        l=data[i]
        if l==0:
            i+=1
            if not jumped: end=i
            break
        if (l&0xC0)==0xC0:
            ptr=struct.unpack('!H', data[i:i+2])[0]&0x3FFF
            if not jumped: end=i+2
            i=ptr; jumped=True; continue
        i+=1; labels.append(data[i:i+l].decode()); i+=l
    return '.'.join(labels), end

def get_a(server,name):
    data=query(server,name,1)
    qd,an=struct.unpack('!HH', data[4:8]); i=12
    for _ in range(qd):
        _,i=parse_name(data,i); i+=4
    out=[]
    for _ in range(an):
        n,i=parse_name(data,i)
        typ,cls,ttl,rdlen=struct.unpack('!HHIH', data[i:i+10]); i+=10
        rdata=data[i:i+rdlen]; i+=rdlen
        if typ==1 and rdlen==4:
            out.append('.'.join(map(str,rdata)))
    return out

for ns in ['dns101.registrar-servers.com','dns102.registrar-servers.com','ns1.lander.d.parity.domains']:
    try:
        nsip=socket.gethostbyname(ns)
    except Exception as e:
        print(ns, 'resolve fail', e); continue
    print('NS', ns, nsip)
    for host in ['sidms.online','scpms-app.sidms.online','sidms.sidms.online']:
        try:
            print(' ', host, get_a(nsip, host))
        except Exception as e:
            print(' ', host, 'err', e)
PY

echo
echo "======== Write production Traefik compose (host network + HTTP-01) ========"
LE_IP=$(getent ahostsv4 acme-v02.api.letsencrypt.org | awk '{print $1; exit}')
cp -a docker-compose.yml "docker-compose.yml.bak.$(date +%Y%m%d%H%M%S)"

cat > docker-compose.yml <<YAML
# Traefik edge for sidms apps.
# Apps keep labels: traefik.http.routers.*.tls.certresolver=cloudflare
# ACME: HTTP-01 on :80 (works once public A records point to this host).
# network_mode:host → host DNS/routing so LE API is reachable (Docker embed DNS was timing out).

services:
  traefik:
    image: traefik:v3.3
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
      - "--log.level=INFO"
      - "--api.dashboard=true"
      - "--api.insecure=true"
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
      - "--certificatesresolvers.cloudflare.acme.caserver=https://acme-v02.api.letsencrypt.org/directory"
    environment:
      - CF_API_EMAIL=\${CF_API_EMAIL}
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
      - "./acme.json:/acme.json"
YAML

# clean file without escape issues
python3 <<PY
from pathlib import Path
le="$LE_IP"
Path('docker-compose.yml').write_text(f'''# Traefik edge for sidms apps.
# Resolver name remains "cloudflare" to match existing container labels.
# HTTP-01 requires public DNS A/AAAA for each host → {le and "this server"} (82.38.44.122).

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
      - "acme-v02.api.letsencrypt.org:{le}"
    command:
      - "--log.level=INFO"
      - "--api.dashboard=true"
      - "--api.insecure=true"
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
      - "--certificatesresolvers.cloudflare.acme.email=${{CF_API_EMAIL:-admin@zeeshad.com}}"
      - "--certificatesresolvers.cloudflare.acme.storage=/acme.json"
    environment:
      - CF_API_EMAIL=${{CF_API_EMAIL}}
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
      - "./acme.json:/acme.json"
''')
print('compose written')
PY

# ensure acme.json permissions
touch acme.json
chmod 600 acme.json

echo "======== Ensure UFW 80/443 ========"
sudo ufw allow 80/tcp >/dev/null || true
sudo ufw allow 443/tcp >/dev/null || true
sudo ufw status | grep -E '80|443|Status' || true

echo "======== Recreate Traefik ========"
docker compose up -d --force-recreate traefik
sleep 5
docker ps --filter name=^traefik$ --format '{{.Names}} {{.Status}}'

echo "======== Wait for DNS A→origin then bounce routers for cert ========"
python3 <<'PY'
import socket, time, subprocess, json, os
ORIGIN='82.38.44.122'
hosts=['scpms-app.sidms.online','sidms.sidms.online','scpms-api.sidms.online','sidms.online']

def ips(h):
    try:
        return sorted({a[4][0] for a in socket.getaddrinfo(h,443,socket.AF_INET)})
    except Exception:
        return []

print('Polling DNS up to 90s for A records →', ORIGIN)
ok=False
for i in range(18):
    states={h:ips(h) for h in hosts}
    print(f'  try {i+1}', states)
    # success if at least scpms-app and sidms point ONLY to origin (or include origin)
    if all(ORIGIN in states[h] for h in ['scpms-app.sidms.online','sidms.sidms.online']):
        # prefer exclusive
        ok=True
        if all(states[h]==[ORIGIN] for h in ['scpms-app.sidms.online','sidms.sidms.online']):
            print('DNS good (exclusive origin)')
        else:
            print('DNS includes origin (may still have parking IPs)')
        break
    time.sleep(5)
else:
    print('DNS NOT pointing to origin yet — cannot finish LE HTTP-01 from here.')
    print('ACTION REQUIRED at Namecheap (domain expires/expired 2026-10-27):')
    print('  1) Renew sidms.online if expired')
    print('  2) Nameservers: either Cloudflare NS from CF dashboard, OR Namecheap BasicDNS')
    print('  3) A records for scpms-app, sidms, scpms-api, @, office, docs → 82.38.44.122')
    print('  4) Remove parking/lander records')
    raise SystemExit(0)

# force Traefik to retry ACME by bouncing labels via container update? recreate scpms frontend is risky.
# Instead: docker kill -s HUP not supported. Touch by restarting traefik once more.
subprocess.check_call(['docker','compose','restart','traefik'])
time.sleep(15)
# show cert
import subprocess as sp
out=sp.check_output('echo | openssl s_client -connect 127.0.0.1:443 -servername scpms-app.sidms.online 2>/dev/null | openssl x509 -noout -subject -issuer -dates', shell=True, text=True)
print(out)
certs=json.load(open('acme.json')).get('cloudflare',{}).get('Certificates')
print('stored', None if certs is None else len(certs))
if certs:
    for c in certs:
        print(' cert', c.get('domain'))
PY

echo "======== Local verify ========"
curl -k -sS -o /dev/null -w 'scpms/login=%{http_code}\n' --max-time 8 --resolve scpms-app.sidms.online:443:127.0.0.1 https://scpms-app.sidms.online/login
curl -k -sS -o /dev/null -w 'sidms=%{http_code}\n' --max-time 8 --resolve sidms.sidms.online:443:127.0.0.1 https://sidms.sidms.online/
docker logs traefik --since 2m 2>&1 | grep -iE 'certificate|acme|ERR' | tail -20 || true

# note about bad CF token
python3 <<'PY'
print('''
NOTE: /home/sidms/traefik/.env CF_DNS_API_TOKEN is a PEM blob (MIIJ...), NOT a Cloudflare API token.
That cannot drive DNS-01. HTTP-01 is configured instead.
When domain is back on Cloudflare NS, create a real Token (Zone:DNS:Edit) or keep HTTP-01.
''')
PY
