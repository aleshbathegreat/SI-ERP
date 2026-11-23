#!/bin/bash
# Switch Traefik ACME to Cloudflare DNS-01 and verify CF API works.
set -euo pipefail
cd /home/sidms/traefik

echo "=== CF env shape ==="
python3 <<'PY'
env={}
for line in open('.env'):
    line=line.strip()
    if not line or line.startswith('#') or '=' not in line: continue
    k,v=line.split('=',1); env[k]=v.strip().strip('"').strip("'")
for k in ['CF_API_EMAIL','CF_DNS_API_TOKEN','CF_API_KEY','CLOUDFLARE_DNS_API_TOKEN']:
    v=env.get(k,'')
    if not v: continue
    print(k, 'len', len(v), 'prefix', repr(v[:8]), 'pem', v.startswith('MII'), 'v1', v.startswith('v1.'))
PY

echo
echo "=== test Cloudflare API ==="
python3 <<'PY'
import json, urllib.request, urllib.error
env={}
for line in open('.env'):
    line=line.strip()
    if not line or line.startswith('#') or '=' not in line: continue
    k,v=line.split('=',1); env[k]=v.strip().strip('"').strip("'")
token=env.get('CF_DNS_API_TOKEN') or env.get('CF_API_KEY') or ''
email=env.get('CF_API_EMAIL','')

def get(headers, path):
    req=urllib.request.Request('https://api.cloudflare.com/client/v4/'+path, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        body=e.read().decode('utf-8','replace')
        try: j=json.loads(body)
        except Exception: j={'raw':body[:300]}
        return e.code, j
    except Exception as e:
        return 0, {'error':str(e)}

# From traefik host network, CF API should be reachable
code,j=get({'Authorization':'Bearer '+token,'Content-Type':'application/json'}, 'user/tokens/verify')
print('bearer_verify', code, j.get('success'), j.get('errors') or j.get('result') or j)
code,j=get({'Authorization':'Bearer '+token,'Content-Type':'application/json'}, 'zones?name=sidms.online')
print('zones_sidms', code, j.get('success'), j.get('errors'))
if j.get('result'):
    z=j['result'][0]
    print(' zone', z.get('name'), z.get('id'), z.get('status'), 'ns', z.get('name_servers'))
    zid=z['id']
    code,j=get({'Authorization':'Bearer '+token,'Content-Type':'application/json'}, f'zones/{zid}/dns_records?per_page=100')
    print(' records', code, 'count', len(j.get('result') or []))
    for rec in (j.get('result') or []):
        if rec.get('type') in ('A','AAAA','CNAME') and any(x in rec.get('name','') for x in ['scpms','sidms','office','si-erp']):
            print(' ', rec['type'], rec['name'], rec.get('content'), 'proxied='+str(rec.get('proxied')))
# also test reachability
import urllib.request
try:
    urllib.request.urlopen('https://api.cloudflare.com/client/v4/ips', timeout=15)
    print('CF API reachable: yes')
except Exception as e:
    print('CF API reachable: no', e)
PY

echo
echo "=== public DNS still ==="
python3 <<'PY'
import socket, json, urllib.request
for h in ['scpms-app.sidms.online','sidms.sidms.online']:
    print(h, sorted({a[4][0] for a in socket.getaddrinfo(h,443,socket.AF_INET)}))
req=urllib.request.Request('https://cloudflare-dns.com/dns-query?name=sidms.online&type=NS', headers={'accept':'application/dns-json'})
print('public NS', [a['data'] for a in json.load(urllib.request.urlopen(req,timeout=15)).get('Answer',[])])
PY

echo
echo "=== rewrite compose for DNS-01 (Cloudflare) ==="
LE=$(getent ahostsv4 acme-v02.api.letsencrypt.org | awk '{print $1; exit}')
cp -a docker-compose.yml "docker-compose.yml.bak.$(date +%Y%m%d%H%M%S)"

# Keep host network (LE + CF API reachability). Use DNS challenge via Cloudflare.
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
      - "acme-v02.api.letsencrypt.org:${LE}"
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
      - "--certificatesresolvers.cloudflare.acme.dnschallenge=true"
      - "--certificatesresolvers.cloudflare.acme.dnschallenge.provider=cloudflare"
      - "--certificatesresolvers.cloudflare.acme.dnschallenge.resolvers=1.1.1.1:53,8.8.8.8:53"
      - "--certificatesresolvers.cloudflare.acme.dnschallenge.propagation.delaybeforechecks=30"
      - "--certificatesresolvers.cloudflare.acme.email=\${CF_API_EMAIL:-admin@zeeshad.com}"
      - "--certificatesresolvers.cloudflare.acme.storage=/acme.json"
    environment:
      - CF_API_EMAIL=\${CF_API_EMAIL}
      - CF_DNS_API_TOKEN=\${CF_DNS_API_TOKEN}
      - CF_ZONE_API_TOKEN=\${CF_DNS_API_TOKEN}
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
      - "./acme.json:/acme.json"
YAML

# fix escaping via python
python3 <<PY
from pathlib import Path
le="$LE"
Path('docker-compose.yml').write_text(f'''services:
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
      - "--certificatesresolvers.cloudflare.acme.dnschallenge=true"
      - "--certificatesresolvers.cloudflare.acme.dnschallenge.provider=cloudflare"
      - "--certificatesresolvers.cloudflare.acme.dnschallenge.resolvers=1.1.1.1:53,8.8.8.8:53"
      - "--certificatesresolvers.cloudflare.acme.dnschallenge.propagation.delaybeforechecks=30"
      - "--certificatesresolvers.cloudflare.acme.email=${{CF_API_EMAIL:-admin@zeeshad.com}}"
      - "--certificatesresolvers.cloudflare.acme.storage=/acme.json"
    environment:
      - CF_API_EMAIL=${{CF_API_EMAIL}}
      - CF_DNS_API_TOKEN=${{CF_DNS_API_TOKEN}}
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
      - "./acme.json:/acme.json"
''')
print('compose ready')
PY

docker compose up -d --force-recreate traefik
sleep 8
echo "=== ACME logs (DNS-01) ==="
sleep 25
docker logs traefik --since 40s 2>&1 | grep -iE 'acme|cloudflare|certificate|ERR|error|DNS' | tail -40 || true
echo | openssl s_client -connect 127.0.0.1:443 -servername scpms-app.sidms.online 2>/dev/null | openssl x509 -noout -subject -issuer -dates 2>/dev/null || true
python3 - <<'PY'
import json
c=json.load(open('acme.json')).get('cloudflare',{}).get('Certificates')
print('stored', 0 if not c else len(c))
if c:
  for x in c: print(' ', x.get('domain'))
PY
curl -k -sS -o /dev/null -w 'scpms/login=%{http_code}\n' --max-time 8 --resolve scpms-app.sidms.online:443:127.0.0.1 https://scpms-app.sidms.online/login
