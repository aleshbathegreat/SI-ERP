#!/bin/bash
set -e
echo "=== public NS for sidms.online (must be Cloudflare if CF dashboard controls DNS) ==="
python3 <<'PY'
import socket,struct,random

def dns_query(name, qtype, server='1.1.1.1'):
    tid=random.randint(0,65535)
    header=struct.pack('!HHHHHH', tid, 0x0100, 1, 0, 0, 0)
    q=b''.join(bytes([len(p)])+p.encode() for p in name.split('.'))+b'\x00'+struct.pack('!HH', qtype, 1)
    s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(5)
    s.sendto(header+q, (server,53))
    data,_=s.recvfrom(4096); s.close()
    return data

def parse_name(data,i):
    labels=[]; jumped=False; end=i
    while True:
        if i>=len(data): return '.', end
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

def answers(name,qtype):
    data=dns_query(name,qtype)
    qd,an,ns,ar=struct.unpack('!HHHH', data[4:12])
    i=12
    for _ in range(qd):
        _,i=parse_name(data,i); i+=4
    out=[]
    total=an+ns+ar
    # parse answer section only for an
    for section_count in (an,):
        for _ in range(section_count):
            n,i=parse_name(data,i)
            typ,cls,ttl,rdlen=struct.unpack('!HHIH', data[i:i+10]); i+=10
            rdata=data[i:i+rdlen]; i+=rdlen
            if typ==1 and rdlen==4:
                out.append(('A', '.'.join(map(str,rdata)), ttl))
            elif typ==2:
                nsname,_=parse_name(data,i-rdlen)
                out.append(('NS', nsname, ttl))
            elif typ==5:
                cname,_=parse_name(data,i-rdlen)
                out.append(('CNAME', cname, ttl))
            else:
                out.append((str(typ), rdata[:20].hex(), ttl))
    return out, an

for label in ['sidms.online','scpms-app.sidms.online','sidms.sidms.online']:
    print('##', label)
    # NS only meaningful at zone apex
    if label=='sidms.online':
        # ask for NS - may be in authority; use dig-like via multiple
        pass
    a,_=answers(label,1)
    print(' A:', a)
print()
# NS via authority using dnspython-less: query and print nscount records from authority by re-query type NS
# Simple: use socket getaddrinfo for known CF check

import urllib.request, json
print('server public IP check')
print(urllib.request.urlopen('https://api.ipify.org', timeout=10).read().decode())
PY

# Use host tools
echo "=== dig-like with python ns ==="
python3 <<'PY'
import subprocess,sys
# try nslookup if present
import shutil
for cmd in (['nslookup','-type=NS','sidms.online','1.1.1.1'],['host','-t','NS','sidms.online','1.1.1.1']):
  if shutil.which(cmd[0]):
    print('CMD', cmd)
    subprocess.run(cmd)
    break
else:
  print('no nslookup/host; using raw')
  import socket
  # Cloudflare NS would be *.ns.cloudflare.com
  for h in ['scpms-app.sidms.online','sidms.sidms.online']:
    print(h, socket.getaddrinfo(h,443,socket.AF_INET))
PY

echo
echo "=== outbound from host to LE ==="
curl -sS --max-time 15 -o /tmp/le.json -w 'host_le_http:%{http_code}\n' https://acme-v02.api.letsencrypt.org/directory || echo host_le_fail
head -c 120 /tmp/le.json; echo

echo
echo "=== outbound from traefik to LE IP ==="
docker exec traefik cat /etc/hosts | grep acme || true
docker exec traefik wget -qO- --timeout=15 https://172.65.32.248/directory 2>&1 | head -c 200 || true
echo
# SNI needed maybe
docker exec traefik wget -qO- --timeout=15 --header='Host: acme-v02.api.letsencrypt.org' https://172.65.32.248/directory 2>&1 | head -c 200 || true
echo

echo
echo "=== traefik status / local login ==="
docker ps --filter name=^traefik$ --format '{{.Names}} {{.Status}}'
curl -k -sS -o /dev/null -w 'scpms/login:%{http_code}\n' --max-time 10 --resolve scpms-app.sidms.online:443:127.0.0.1 https://scpms-app.sidms.online/login

echo
echo "=== expected Cloudflare NS examples vs actual ==="
echo "If dashboard is Cloudflare but public NS is lander.d.parity.domains, CF records are ignored by the internet."
