#!/bin/bash
# Diagnose why browser cannot reach Traefik; fix only DNS for sidms/scpms if CF token works.
# Does NOT restart Traefik or other app containers.
set -e

echo "=== iptables 443 hits (are packets arriving?) ==="
sudo iptables -L ufw-user-input -n -v | grep -E 'dpt:80|dpt:443|Chain' | head -20
sudo iptables -L INPUT -n -v | head -5

echo
echo "=== listening ==="
ss -lntp | grep -E ':80|:443'

echo
echo "=== Cloudflare DNS for the two apps ==="
python3 <<'PY'
import json, urllib.request
env={}
for line in open('/home/sidms/traefik/.env'):
    line=line.strip()
    if not line or line.startswith('#') or '=' not in line: continue
    k,v=line.split('=',1)
    env[k]=v.strip().strip('"').strip("'")
token=env.get('CF_DNS_API_TOKEN') or ''
print('token_len', len(token))
if not token:
    raise SystemExit(0)
hdr={'Authorization':'Bearer '+token,'Content-Type':'application/json'}
def get(url):
    req=urllib.request.Request(url, headers=hdr)
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)
try:
    z=get('https://api.cloudflare.com/client/v4/zones?name=sidms.online')
except Exception as e:
    print('CF zone error', e)
    raise SystemExit(1)
print('zone_ok', z.get('success'), z.get('errors'))
if not z.get('result'):
    raise SystemExit('no zone')
zid=z['result'][0]['id']
print('zone_id', zid)
data=get(f'https://api.cloudflare.com/client/v4/zones/{zid}/dns_records?per_page=200')
want=('sidms.sidms.online','scpms-app.sidms.online','scpms-api.sidms.online','sidms.online')
for rec in data.get('result') or []:
    if rec.get('name') in want or rec.get('name') in ('sidms.online',):
        print(rec['type'], rec['name'], rec.get('content'), 'proxied='+str(rec.get('proxied')), 'ttl='+str(rec.get('ttl')), 'id='+rec['id'])
# also print any A/AAAA for sidms.online zone that point to the weird IPs
print('--- A records pointing to 2.59/104.219/82.38 ---')
for rec in data.get('result') or []:
    if rec.get('type') in ('A','AAAA') and any(x in str(rec.get('content')) for x in ('2.59.','104.219.','82.38.')):
        print(rec['type'], rec['name'], rec['content'], 'proxied='+str(rec.get('proxied')))
PY
