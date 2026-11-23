#!/bin/bash
# Point JMC at mushaz.com, ensure CF DNS A records, bring stack up.
set -euo pipefail
ORIGIN=82.38.44.122
APP=si-erp.mushaz.com
API=si-erp-api.mushaz.com
JMC=/home/sidms/jmc
TR=/home/sidms/traefik

echo "=== CF zone mushaz.com + ensure A records ==="
python3 <<PY
import json, urllib.request, urllib.error
ORIGIN='$ORIGIN'
hosts=['si-erp.mushaz.com','si-erp-api.mushaz.com','mushaz.com','www.mushaz.com']

env={}
for line in open('$TR/.env'):
    line=line.strip()
    if not line or line.startswith('#') or '=' not in line: continue
    k,v=line.split('=',1); env[k]=v.strip().strip('"').strip("'")
token=env['CF_DNS_API_TOKEN']
hdr={'Authorization':'Bearer '+token,'Content-Type':'application/json'}

def api(method, path, body=None):
    data=None if body is None else json.dumps(body).encode()
    req=urllib.request.Request('https://api.cloudflare.com/client/v4/'+path, data=data, method=method, headers=hdr)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode())

z=api('GET','zones?name=mushaz.com')
print('zones', z.get('success'), z.get('errors'))
if not z.get('result'):
    # list zones to help
    allz=api('GET','zones?per_page=50')
    print('available zones:', [x.get('name') for x in (allz.get('result') or [])])
    raise SystemExit('No mushaz.com zone for this CF token')
zone=z['result'][0]
zid=zone['id']
print('zone', zid, zone['status'], 'ns', zone.get('name_servers'))

# public NS check
import socket
req=urllib.request.Request('https://cloudflare-dns.com/dns-query?name=mushaz.com&type=NS', headers={'accept':'application/dns-json'})
ns=[a['data'] for a in json.load(urllib.request.urlopen(req,timeout=15)).get('Answer',[])]
print('public NS', ns)
cfns=set(x.lower() for x in (zone.get('name_servers') or []))
pub=set(x.rstrip('.').lower() for x in ns)
if cfns and pub and pub!=cfns:
    print('WARNING: public NS != Cloudflare NS — certs/DNS may fail until registrar uses:', sorted(cfns))

recs=api('GET', f'zones/{zid}/dns_records?per_page=200').get('result') or []
by_name_type={}
for r in recs:
    by_name_type[(r['name'], r['type'])]=r

def upsert_a(fqdn):
    key=(fqdn,'A')
    existing=by_name_type.get(key)
    body={'type':'A','name':fqdn,'content':ORIGIN,'ttl':1,'proxied':False}  # DNS only for ACME HTTP or DNS-01; proxied=false better for origin certs; DNS-01 works either way
    # For Cloudflare DNS-01, proxied can stay true; use proxied False so HTTP also works if needed
    if existing:
        if existing.get('content')==ORIGIN:
            print('OK', fqdn, existing.get('content'), 'proxied='+str(existing.get('proxied')))
            # ensure not conflicting
            return
        print('UPDATE', fqdn, existing.get('content'), '->', ORIGIN)
        res=api('PUT', f'zones/{zid}/dns_records/{existing["id"]}', body)
        print(' ', res.get('success'), res.get('errors'))
    else:
        print('CREATE', fqdn, ORIGIN)
        res=api('POST', f'zones/{zid}/dns_records', body)
        print(' ', res.get('success'), res.get('errors'))

for h in ['si-erp.mushaz.com','si-erp-api.mushaz.com']:
    upsert_a(h)

# show current A for mushaz
for r in recs:
    if r.get('type') in ('A','CNAME') and 'mushaz.com' in r.get('name',''):
        print('existing', r['type'], r['name'], r.get('content'), 'proxied='+str(r.get('proxied')))
PY

echo
echo "=== update JMC compose defaults to mushaz.com ==="
cd "$JMC"
# patch docker-compose.yml in place on server (deployed copy)
python3 <<'PY'
from pathlib import Path
p=Path('/home/sidms/jmc/docker-compose.yml')
t=p.read_text()
t=t.replace('si-erp-api.sidms.online','si-erp-api.mushaz.com')
t=t.replace('si-erp.sidms.online','si-erp.mushaz.com')
t=t.replace('sidms.online','mushaz.com')  # any leftover comments
p.write_text(t)
print('patched compose hosts')
# ensure .env
envp=Path('/home/sidms/jmc/.env')
lines=[]
if envp.exists():
    lines=envp.read_text().splitlines()
kv={}
for line in lines:
    if '=' in line and not line.strip().startswith('#'):
        k,v=line.split('=',1); kv[k]=v
updates={
  'APP_DOMAIN':'si-erp.mushaz.com',
  'API_DOMAIN':'si-erp-api.mushaz.com',
  'DJANGO_ALLOWED_HOSTS':'si-erp-api.mushaz.com,si-erp.mushaz.com,localhost,127.0.0.1',
  'DJANGO_CSRF_TRUSTED_ORIGINS':'https://si-erp.mushaz.com,https://si-erp-api.mushaz.com',
  'CORS_ALLOWED_ORIGINS':'https://si-erp.mushaz.com',
  'FRONTEND_URL':'https://si-erp.mushaz.com',
  'PLATFORM_ROOT_DOMAIN':'si-erp.mushaz.com',
  'PLATFORM_HOSTS':'si-erp.mushaz.com,si-erp-api.mushaz.com',
  'NEXT_PUBLIC_API_URL':'https://si-erp-api.mushaz.com/api',
}
for k,v in updates.items():
    kv[k]=v
if 'DJANGO_SECRET_KEY' not in kv or not kv['DJANGO_SECRET_KEY'] or 'change-me' in kv['DJANGO_SECRET_KEY']:
    import secrets
    kv['DJANGO_SECRET_KEY']=secrets.token_urlsafe(48)
# preserve RUN_SEED if set
out=[]
# keep unknown keys
for k,v in kv.items():
    out.append(f'{k}={v}')
envp.write_text('\n'.join(out)+'\n')
print('wrote .env domains')
PY

echo
echo "=== ensure images exist / up jmc ==="
# Prefer existing images; build only if missing
if ! docker image inspect jmc-api >/dev/null 2>&1 && ! docker image inspect jmc_api >/dev/null 2>&1; then
  echo 'building api (may use cached layers)'
  docker compose build api || true
fi
docker compose up -d --remove-orphans
sleep 8
docker ps --filter name=jmc_ --format 'table {{.Names}}\t{{.Status}}'

echo
echo "=== wait ACME / local check ==="
sleep 20
for h in si-erp.mushaz.com si-erp-api.mushaz.com; do
  echo -n "$h cert: "
  echo | openssl s_client -connect 127.0.0.1:443 -servername "$h" 2>/dev/null | openssl x509 -noout -subject -issuer 2>/dev/null || echo none
done
curl -k -sS -o /dev/null -w 'web=%{http_code}\n' --max-time 10 --resolve si-erp.mushaz.com:443:127.0.0.1 https://si-erp.mushaz.com/ || true
curl -k -sS -o /dev/null -w 'api_health=%{http_code}\n' --max-time 10 --resolve si-erp-api.mushaz.com:443:127.0.0.1 https://si-erp-api.mushaz.com/api/health/ || true
docker logs traefik --since 1m 2>&1 | grep -iE 'si-erp|mushaz|acme|ERR' | tail -20 || true

echo
echo "=== public resolve ==="
python3 - <<'PY'
import socket
for h in ['si-erp.mushaz.com','si-erp-api.mushaz.com']:
  try:
    print(h, sorted({a[4][0] for a in socket.getaddrinfo(h,443,socket.AF_INET)}))
  except Exception as e:
    print(h, e)
PY
echo "URLs: https://si-erp.mushaz.com/  https://si-erp-api.mushaz.com/api/health/"
