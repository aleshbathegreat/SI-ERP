#!/bin/bash
set -e
echo "=== acme cert domains ==="
python3 - <<'PY'
import json,base64,re
from pathlib import Path
p=Path('/home/sidms/traefik/acme.json')
d=json.loads(p.read_text())
certs=[]
def walk(o,path=''):
  if isinstance(o,dict):
    if 'domain' in o and 'certificate' in o:
      dom=o.get('domain')
      certs.append(dom)
    for k,v in o.items():
      walk(v, path+'.'+k)
  elif isinstance(o,list):
    for i,v in enumerate(o):
      walk(v, path+f'[{i}]')
walk(d)
print('cert entries:', len(certs))
for c in certs:
  print(c)
# also dump top keys
print('top keys', list(d.keys()))
for k,v in d.items():
  if isinstance(v,dict):
    print(k, '->', list(v.keys()))
    if 'Certificates' in v:
      for c in v['Certificates'] or []:
        print(' ', c.get('domain'))
PY

echo "=== traefik api 9080 jmc/sipulse ==="
curl -sS --max-time 5 http://127.0.0.1:9080/api/http/routers | python3 - <<'PY'
import sys,json
d=json.load(sys.stdin)
for r in d:
  name=r.get('name','')
  rule=str(r.get('rule',''))
  if any(x in name.lower() or x in rule.lower() for x in ['jmc','si-erp','sipulse','scpms']):
    tls=r.get('tls')
    print(f"{name} status={r.get('status')} tls={tls} rule={rule}")
PY

echo "=== who owns DNS ips ==="
for ip in 104.219.250.37 2.59.170.20 82.38.44.122; do
  echo -n "$ip -> "
  dig +short -x $ip 2>/dev/null | head -1 || true
  curl -sS --max-time 3 "https://ipinfo.io/$ip/json" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('org'), d.get('city'), d.get('hostname'))" 2>/dev/null || echo
done

echo "=== traefik DNS resolve test ==="
docker exec traefik sh -c 'getent hosts acme-v02.api.letsencrypt.org || nslookup acme-v02.api.letsencrypt.org || ping -c1 1.1.1.1' 2>&1 | head -20

echo "=== host DNS ==="
getent hosts acme-v02.api.letsencrypt.org || true
resolvectl status 2>/dev/null | head -40 || cat /etc/resolv.conf

echo "=== public curl from host to si-erp and sipulse ==="
for h in si-erp.sidms.online sipulse-frontend.sidms.online scpms-app.sidms.online; do
  echo "--- $h ---"
  curl -sS -o /dev/null -w "http=%{http_code} ssl=%{ssl_verify_result} err=%{errormsg}\n" --max-time 15 "https://$h/" 2>&1 | tail -3
done

echo "=== docker compose labels compare sipulse vs jmc ==="
docker inspect sipulse-frontend --format '{{json .Config.Labels}}' 2>/dev/null | python3 -m json.tool 2>/dev/null | head -40 || docker ps --format '{{.Names}}' | head -30
