#!/bin/bash
set -euo pipefail
ORIGIN=82.38.44.122
cd /home/sidms/traefik

echo "=== 1) Current public DNS ==="
python3 <<'PY'
import socket, json, urllib.request
ORIGIN='82.38.44.122'
hosts=['scpms-app.sidms.online','sidms.sidms.online','scpms-api.sidms.online','sidms.online','office.sidms.online']
for h in hosts:
    try:
        ips=sorted({a[4][0] for a in socket.getaddrinfo(h,443,socket.AF_INET)})
    except Exception as e:
        ips=[str(e)]
    ok='OK' if ips==[ORIGIN] else ('PARTIAL' if ORIGIN in ips else 'BAD')
    print(f'{ok:8} {h} -> {ips}')
req=urllib.request.Request('https://cloudflare-dns.com/dns-query?name=sidms.online&type=NS', headers={'accept':'application/dns-json'})
ns=json.load(urllib.request.urlopen(req, timeout=15))
print('NS:', [a['data'] for a in ns.get('Answer',[])])
# RDAP
for url in ['https://rdap.identitydigital.services/rdap/domain/sidms.online','https://rdap.org/domain/sidms.online']:
    try:
        d=json.load(urllib.request.urlopen(url, timeout=20))
        print('RDAP status', d.get('status'))
        print('RDAP NS', [n.get('ldhName') for n in (d.get('nameservers') or [])])
        for e in d.get('events') or []:
            if e.get('eventAction') in ('expiration','last changed','registration'):
                print('RDAP', e.get('eventAction'), e.get('eventDate'))
        break
    except Exception as e:
        print('rdap', url, e)
PY

echo
echo "=== 2) Query registrar NS directly ==="
python3 <<'PY'
import socket,struct,random
def query(server, name, qtype=1):
    tid=random.randint(0,65535)
    header=struct.pack('!HHHHHH', tid, 0x0100, 1, 0, 0, 0)
    q=b''.join(bytes([len(p)])+p.encode() for p in name.split('.'))+b'\x00'+struct.pack('!HH', qtype, 1)
    s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(8)
    s.sendto(header+q,(server,53)); data,_=s.recvfrom(4096); s.close(); return data
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
        if typ==1 and rdlen==4: out.append('.'.join(map(str,rdata)))
    return out
for ns in ['dns101.registrar-servers.com','dns102.registrar-servers.com']:
    try:
        ip=socket.gethostbyname(ns)
        print(ns, ip)
        for h in ['sidms.online','scpms-app.sidms.online','sidms.sidms.online','scpms-api.sidms.online','office.sidms.online']:
            print(' ', h, get_a(ip,h))
    except Exception as e:
        print(ns, e)
PY

echo
echo "=== 3) Traefik compose + UFW ==="
LE_IP=$(getent ahostsv4 acme-v02.api.letsencrypt.org | awk '{print $1; exit}')
echo "LE_IP=$LE_IP"
cp -a docker-compose.yml "docker-compose.yml.bak.$(date +%Y%m%d%H%M%S)" 2>/dev/null || true

python3 <<PY
from pathlib import Path
le = """$LE_IP"""
Path('docker-compose.yml').write_text(f"""services:
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
""")
print('compose written')
PY
touch acme.json; chmod 600 acme.json
sudo ufw allow 80/tcp >/dev/null 2>&1 || true
sudo ufw allow 443/tcp >/dev/null 2>&1 || true

docker compose up -d --force-recreate traefik
sleep 6
docker ps --filter name=^traefik$ --format '{{.Names}} {{.Status}}'

echo
echo "=== 4) If DNS already points here, force cert retry ==="
python3 <<'PY'
import socket, json, subprocess, time
ORIGIN='82.38.44.122'
need=['scpms-app.sidms.online','sidms.sidms.online']
def ips(h):
    try: return sorted({a[4][0] for a in socket.getaddrinfo(h,443,socket.AF_INET)})
    except: return []
states={h:ips(h) for h in need+['scpms-api.sidms.online','sidms.online','office.sidms.online']}
print(states)
ready=all(ORIGIN in states[h] for h in need)
if not ready:
    print('BLOCKED: public DNS still not on this server.')
    print('Namecheap must set A records for these hosts to', ORIGIN)
    print('Domain RDAP showed expiration 2026-10-27 — renew if needed.')
    raise SystemExit(2)
print('DNS includes origin — restarting Traefik to retry ACME')
subprocess.check_call(['docker','compose','restart','traefik'])
time.sleep(20)
out=subprocess.check_output('echo | openssl s_client -connect 127.0.0.1:443 -servername scpms-app.sidms.online 2>/dev/null | openssl x509 -noout -subject -issuer -dates', shell=True, text=True)
print(out)
d=json.load(open('acme.json'))
certs=d.get('cloudflare',{}).get('Certificates')
print('stored_certs', 0 if not certs else len(certs))
if certs:
    for c in certs: print(' ', c.get('domain'))
PY
ec=$?

echo
echo "=== 5) Local app check ==="
curl -k -sS -o /dev/null -w 'scpms/login=%{http_code}\n' --max-time 8 --resolve scpms-app.sidms.online:443:127.0.0.1 https://scpms-app.sidms.online/login || true
curl -k -sS -o /dev/null -w 'sidms=%{http_code}\n' --max-time 8 --resolve sidms.sidms.online:443:127.0.0.1 https://sidms.sidms.online/ || true
docker logs traefik --since 1m 2>&1 | grep -iE 'certificate|acme|ERR' | tail -15 || true
exit $ec
