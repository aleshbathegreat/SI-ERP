#!/bin/bash
set -euo pipefail
cd /home/sidms/traefik

echo "=== Cloudflare expected NS (from API) ==="
python3 <<'PY'
import json, urllib.request
env={}
for line in open('.env'):
    line=line.strip()
    if not line or line.startswith('#') or '=' not in line: continue
    k,v=line.split('=',1); env[k]=v.strip().strip('"').strip("'")
token=env['CF_DNS_API_TOKEN']
req=urllib.request.Request('https://api.cloudflare.com/client/v4/zones?name=sidms.online',
    headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
z=json.load(urllib.request.urlopen(req, timeout=20))['result'][0]
print('zone_status', z['status'])
print('CF_name_servers', z.get('name_servers'))
print('original_name_servers', z.get('original_name_servers'))
open('/tmp/cf_ns.txt','w').write('\n'.join(z.get('name_servers') or []))
PY
echo "SET THESE AT NAMECHEAP → Domain → Nameservers → Custom DNS:"
cat /tmp/cf_ns.txt

echo
echo "=== public NS now ==="
python3 <<'PY'
import json, urllib.request
req=urllib.request.Request('https://cloudflare-dns.com/dns-query?name=sidms.online&type=NS', headers={'accept':'application/dns-json'})
ans=[a['data'].rstrip('.') for a in json.load(urllib.request.urlopen(req,timeout=15)).get('Answer',[])]
print(ans)
cf=open('/tmp/cf_ns.txt').read().split()
if set(x.lower() for x in ans)==set(x.lower() for x in cf):
    print('PUBLIC_NS_OK')
else:
    print('PUBLIC_NS_WRONG — registrar still on', ans)
    print('Namecheap: Domain List → sidms.online → Manage → Nameservers')
    print('  Choose Custom DNS and paste the two Cloudflare NS above.')
    print('  Remove lander.d.parity.domains / dns101.registrar-servers.com')
PY

# Apply DNS-01 compose
LE=$(getent ahostsv4 acme-v02.api.letsencrypt.org | awk '{print $1; exit}')
cp -a docker-compose.yml "docker-compose.yml.bak.$(date +%Y%m%d%H%M%S)" 2>/dev/null || true
cp -f /home/sidms/jmc/traefik-cf-dns.yml docker-compose.yml
sed -i "s/172.65.32.248/${LE}/" docker-compose.yml
docker compose up -d --force-recreate traefik
sleep 5
docker ps --filter name=^traefik$ --format '{{.Names}} {{.Status}}'

echo
echo "=== poll up to 3 min for CF NS, then certs ==="
python3 <<'PY'
import json, urllib.request, time, subprocess, socket
cf=set(x.lower() for x in open('/tmp/cf_ns.txt').read().split() if x)
ok=False
for i in range(36):
    req=urllib.request.Request('https://cloudflare-dns.com/dns-query?name=sidms.online&type=NS', headers={'accept':'application/dns-json'})
    ans=set(a['data'].rstrip('.').lower() for a in json.load(urllib.request.urlopen(req,timeout=15)).get('Answer',[]))
    print(f'poll {i+1}', sorted(ans))
    if ans==cf:
        ok=True; break
    # also accept if A for scpms already points to origin via CF
    try:
        ips=sorted({a[4][0] for a in socket.getaddrinfo('scpms-app.sidms.online',443,socket.AF_INET)})
    except Exception:
        ips=[]
    print('  scpms A', ips)
    if ips and all(not x.startswith('104.219') and not x.startswith('2.59.') for x in ips):
        # likely CF proxy IPs (104.16 etc) or origin
        if '82.38.44.122' in ips or any(x.startswith('104.1') or x.startswith('172.6') or x.startswith('104.2') for x in ips):
            if not any(x in ('104.219.250.37','2.59.170.20') for x in ips):
                print('A records left parking — continue')
                ok=True; break
    time.sleep(5)

if not ok:
    print('NS not updated yet. Traefik is on Cloudflare DNS-01 and ready.')
    print('After you set Cloudflare NS at Namecheap, run: cd ~/traefik && docker compose restart traefik')
    raise SystemExit(0)

print('DNS looks good — restart Traefik for ACME')
subprocess.check_call(['docker','compose','restart','traefik'])
time.sleep(45)
out=subprocess.check_output('echo | openssl s_client -connect 127.0.0.1:443 -servername scpms-app.sidms.online 2>/dev/null | openssl x509 -noout -subject -issuer -dates', shell=True, text=True)
print(out)
certs=json.load(open('acme.json')).get('cloudflare',{}).get('Certificates')
print('stored', 0 if not certs else len(certs))
if certs:
    for c in certs: print(' ', c.get('domain'))
logs=subprocess.check_output(['docker','logs','traefik','--since','1m'], stderr=subprocess.STDOUT, text=True)
for line in logs.splitlines():
    if any(x in line.lower() for x in ['acme','certificate','err','error','dns']):
        print(line[-300:])
PY

curl -k -sS -o /dev/null -w 'scpms/login=%{http_code}\n' --max-time 8 --resolve scpms-app.sidms.online:443:127.0.0.1 https://scpms-app.sidms.online/login
