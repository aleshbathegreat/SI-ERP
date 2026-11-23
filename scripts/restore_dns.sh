#!/bin/bash
set -e
echo "=== host IPs / routes ==="
ip -4 addr
echo
ip route
echo
echo "=== Contabo / cloud-init network ==="
ls /etc/netplan 2>/dev/null; cat /etc/netplan/*.yaml 2>/dev/null | head -80
echo
echo "=== Cloudflare API debug ==="
python3 <<'PY'
import json, urllib.request, urllib.error, ssl
env={}
for line in open('/home/sidms/traefik/.env'):
    line=line.strip()
    if not line or line.startswith('#') or '=' not in line: continue
    k,v=line.split('=',1)
    env[k]=v.strip().strip('"').strip("'")
token=env.get('CF_DNS_API_TOKEN') or ''
email=env.get('CF_API_EMAIL') or ''
print('email', email, 'token_prefix', token[:6], 'token_len', len(token))

def call(url, method='GET', body=None):
    data=None if body is None else json.dumps(body).encode()
    req=urllib.request.Request(url, data=data, method=method, headers={
        'Authorization': 'Bearer '+token,
        'Content-Type': 'application/json',
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        raw=e.read().decode('utf-8','replace')
        try:
            j=json.loads(raw)
        except Exception:
            j={'raw': raw[:500]}
        return e.code, j

# verify token
code,j=call('https://api.cloudflare.com/client/v4/user/tokens/verify')
print('verify', code, j.get('success'), j.get('errors') or j.get('messages') or j.get('result'))

# list zones
code,j=call('https://api.cloudflare.com/client/v4/zones?per_page=50')
print('zones', code, 'success', j.get('success'), 'errors', j.get('errors'))
zones=j.get('result') or []
for z in zones:
    print(' ZONE', z.get('name'), z.get('id'), z.get('status'))

# try sidms.online specifically
code,j=call('https://api.cloudflare.com/client/v4/zones?name=sidms.online')
print('sidms.online query', code, j)

# if we have a zone, dump A records for the two hosts
zid=None
for z in zones:
    if z.get('name')=='sidms.online':
        zid=z['id']
if not zid and (j.get('result') or []):
    zid=j['result'][0]['id']
if zid:
    code,j=call(f'https://api.cloudflare.com/client/v4/zones/{zid}/dns_records?per_page=200')
    print('records', code, 'count', len(j.get('result') or []))
    for rec in j.get('result') or []:
        name=rec.get('name','')
        if any(x in name for x in ['sidms.sidms','scpms-app','scpms-api','si-erp','office','docs']) or name in ('sidms.online','www.sidms.online'):
            print(f"  {rec['type']:5} {name:40} {rec.get('content')} proxied={rec.get('proxied')} id={rec['id']}")
else:
    print('NO ZONE ACCESS for sidms.online')
PY

echo
echo "=== whois-ish on DNS IPs via ipinfo ==="
for ip in 2.59.170.20 104.219.250.37 82.38.44.122; do
  echo -n "$ip: "
  curl -sS --max-time 8 "https://ipinfo.io/$ip/json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('org'), d.get('city'), d.get('region'))" 2>/dev/null || echo fail
done

echo
echo "=== can host reach those DNS IPs on 443? ==="
for ip in 2.59.170.20 104.219.250.37; do
  timeout 5 bash -c "echo >/dev/tcp/$ip/443" 2>/dev/null && echo "$ip:443 open" || echo "$ip:443 closed/timeout"
done
