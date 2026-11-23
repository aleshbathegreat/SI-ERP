#!/bin/bash
# Traefik/DevOps recovery for sidms.online apps (no JMC start).
set -euo pipefail

ORIGIN_IP="82.38.44.122"
TRDIR=/home/sidms/traefik
cd "$TRDIR"

echo "======== 1) LIVE PUBLIC DNS ========"
python3 <<'PY'
import socket, json, urllib.request
print('origin expected: 82.38.44.122')
for h in ['sidms.online','scpms-app.sidms.online','sidms.sidms.online','scpms-api.sidms.online']:
    try:
        ips=sorted({a[4][0] for a in socket.getaddrinfo(h,443,socket.AF_INET)})
    except Exception as e:
        ips=str(e)
    print(f'  {h} -> {ips}')
# NS via Cloudflare DoH
req=urllib.request.Request(
    'https://cloudflare-dns.com/dns-query?name=sidms.online&type=NS',
    headers={'accept':'application/dns-json'})
ns=json.load(urllib.request.urlopen(req, timeout=15))
print('NS:', [a['data'] for a in ns.get('Answer',[])])
PY

echo
echo "======== 2) RDAP / expiry ========"
python3 <<'PY'
import json, urllib.request
try:
    d=json.load(urllib.request.urlopen('https://rdap.identitydigital.services/rdap/domain/sidms.online', timeout=20))
except Exception as e:
    try:
        d=json.load(urllib.request.urlopen('https://rdap.org/domain/sidms.online', timeout=20))
    except Exception as e2:
        print('rdap fail', e, e2); raise SystemExit
print('ldhName', d.get('ldhName'))
print('status', d.get('status'))
for e in d.get('events') or []:
    print('event', e.get('eventAction'), e.get('eventDate'))
print('nameservers', [n.get('ldhName') for n in (d.get('nameservers') or [])])
for ent in d.get('entities') or []:
    roles=ent.get('roles')
    if roles: print('entity roles', roles)
PY

echo
echo "======== 3) Cloudflare API (token shape) ========"
python3 <<'PY'
import json, urllib.request, urllib.error
env={}
for line in open('/home/sidms/traefik/.env'):
    line=line.strip()
    if not line or line.startswith('#') or '=' not in line: continue
    k,v=line.split('=',1); env[k]=v.strip().strip('"').strip("'")
token=env.get('CF_DNS_API_TOKEN','')
email=env.get('CF_API_EMAIL','')
print('email', email)
print('token_len', len(token), 'starts_MII', token.startswith('MII'), 'starts_v1', token.startswith('v1.'))
# Bearer token
def call(headers, path):
    req=urllib.request.Request('https://api.cloudflare.com/client/v4/'+path, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())
code,j=call({'Authorization':'Bearer '+token,'Content-Type':'application/json'}, 'user/tokens/verify')
print('bearer_verify', code, j.get('success'), j.get('errors'))
# maybe it's global API key wrongly named
code,j=call({'X-Auth-Email':email,'X-Auth-Key':token,'Content-Type':'application/json'}, 'user')
print('global_key_user', code, j.get('success'), j.get('errors'))
PY

echo
echo "======== 4) Search Namecheap / real CF token files (paths only + key names) ========"
python3 <<'PY'
import os,re
roots=['/home/sidms']
pat=re.compile(r'(CF_API_KEY|CF_DNS_API_TOKEN|CLOUDFLARE_API|NAMECHEAP_API|NAMECHEAP_KEY|ApiUser|ApiKey)\s*=\s*(.+)', re.I)
found=[]
for root in roots:
  for dirpath,_,files in os.walk(root):
    if any(x in dirpath for x in ['.cursor-server','.npm','.cache','node_modules','.git']):
      continue
    for f in files:
      if f.endswith(('.env','.env.local','.env.production','.ini','.cfg')) or f in ('credentials','secrets'):
        path=os.path.join(dirpath,f)
        try:
          txt=open(path,'r',errors='ignore').read()
        except Exception:
          continue
        for m in pat.finditer(txt):
          val=m.group(2).strip().strip('"').strip("'")
          found.append((path,m.group(1),len(val),val[:4]+'…', val.startswith('MII'), val.startswith('v1.')))
print('matches', len(found))
for row in found[:40]:
  print('%s | %s | len=%s | %s | pem=%s v1=%s' % row)
PY

echo
echo "======== 5) Current Traefik / local health ========"
docker ps --filter name=^traefik$ --format '{{.Names}} {{.Status}} {{.Ports}}'
curl -k -sS -o /dev/null -w 'scpms/login=%{http_code}\n' --max-time 8 --resolve scpms-app.sidms.online:443:127.0.0.1 https://scpms-app.sidms.online/login || true
curl -k -sS -o /dev/null -w 'sidms/=%{http_code}\n' --max-time 8 --resolve sidms.sidms.online:443:127.0.0.1 https://sidms.sidms.online/ || true
echo | openssl s_client -connect 127.0.0.1:443 -servername scpms-app.sidms.online 2>/dev/null | openssl x509 -noout -subject -issuer 2>/dev/null || true
