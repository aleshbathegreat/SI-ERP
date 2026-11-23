#!/bin/bash
set -e
echo "=== NS / SOA for sidms.online ==="
python3 <<'PY'
import socket,struct,random
# minimal DNS query via 8.8.8.8 for NS and A

def query(name, qtype):
    # qtype 1=A 2=NS
    tid=random.randint(0,65535)
    flags=0x0100
    header=struct.pack('!HHHHHH', tid, flags, 1, 0, 0, 0)
    q=b''
    for p in name.split('.'):
        q+=bytes([len(p)])+p.encode()
    q+=b'\x00'+struct.pack('!HH', qtype, 1)
    sock=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)
    sock.sendto(header+q, ('8.8.8.8',53))
    data,_=sock.recvfrom(4096)
    sock.close()
    return data

def parse_name(data, i):
    labels=[]
    jumped=False
    orig=i
    while True:
        if i>=len(data):
            break
        l=data[i]
        if l==0:
            i+=1
            break
        if (l & 0xC0)==0xC0:
            ptr=struct.unpack('!H', data[i:i+2])[0] & 0x3FFF
            if not jumped:
                orig=i+2
            i=ptr
            jumped=True
            continue
        i+=1
        labels.append(data[i:i+l].decode('utf-8','replace'))
        i+=l
    return '.'.join(labels), (orig if jumped else i)

def parse_answers(data, qtype_want):
    if len(data)<12: return []
    qd,an=struct.unpack('!HH', data[4:8])
    i=12
    for _ in range(qd):
        _,i=parse_name(data,i)
        i+=4
    out=[]
    for _ in range(an):
        name,i=parse_name(data,i)
        typ,cls,ttl,rdlen=struct.unpack('!HHIH', data[i:i+10]); i+=10
        rdata=data[i:i+rdlen]; i+=rdlen
        if typ==1 and rdlen==4:
            out.append((name,'A','.'.join(str(b) for b in rdata),ttl))
        elif typ==2:
            ns,_=parse_name(data,i-rdlen)
            # wrong - need parse from start of rdata
            ns,_=parse_name(data, i-rdlen)
            out.append((name,'NS',ns,ttl))
        else:
            out.append((name,str(typ),rdata[:40],ttl))
    return out

for label,qt in [('sidms.online',2),('sidms.sidms.online',1),('scpms-app.sidms.online',1)]:
    try:
        data=query(label, qt)
        print(label, 'qtype', qt)
        # dump raw answer count
        print('  ancount', struct.unpack('!H', data[6:8])[0], 'nscount', struct.unpack('!H', data[8:10])[0])
        # Better use dig via docker if available
    except Exception as e:
        print(label, e)
PY

# use docker run with dnsutils if present, else host getent
if docker images | grep -q dnsutils; then true; fi
docker run --rm --network host busybox:1.36 nslookup -type=NS sidms.online 8.8.8.8 2>/dev/null || true
docker run --rm --network host busybox:1.36 nslookup sidms.sidms.online 8.8.8.8 2>/dev/null || true
docker run --rm --network host busybox:1.36 nslookup scpms-app.sidms.online 8.8.8.8 2>/dev/null || true

echo
echo "=== .env token shape (redacted) ==="
python3 <<'PY'
for line in open('/home/sidms/traefik/.env'):
  if '=' not in line or line.strip().startswith('#'): continue
  k,v=line.split('=',1)
  v=v.strip()
  print(k, 'len', len(v), 'starts', repr(v[:8]), 'ends', repr(v[-4:]), 'has_space', ' ' in v, 'has_quote', '"' in v or "'" in v)
PY

echo
echo "=== listen while external probe note ==="
# show docker vs host ownership of 443
sudo ss -lntp | grep -E ':80|:443'
sudo iptables -L DOCKER -n -v 2>/dev/null | head -20
sudo iptables -t nat -L DOCKER -n -v 2>/dev/null | head -20

echo
echo "=== HOSTKEY / provider firewall tools ==="
which csf nft firewall-cmd 2>/dev/null; sudo nft list ruleset 2>/dev/null | grep -E 'dport (80|443)' | head -20
