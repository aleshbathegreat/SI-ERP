#!/bin/bash
# Update Namecheap BasicDNS A records → 82.38.44.122
# Requires: NAMECHEAP_API_USER NAMECHEAP_API_KEY NAMECHEAP_USERNAME
# Optional: NAMECHEAP_CLIENT_IP (defaults to server public IP)
set -euo pipefail
ORIGIN=82.38.44.122
SLD=sidms
TLD=online

: "${NAMECHEAP_API_USER:?set NAMECHEAP_API_USER}"
: "${NAMECHEAP_API_KEY:?set NAMECHEAP_API_KEY}"
: "${NAMECHEAP_USERNAME:?set NAMECHEAP_USERNAME}"

CLIENT_IP="${NAMECHEAP_CLIENT_IP:-$(curl -4 -sS --max-time 10 ifconfig.me)}"
echo "ClientIp=$CLIENT_IP Origin=$ORIGIN"

BASE="https://api.namecheap.com/xml.response"
AUTH="ApiUser=${NAMECHEAP_API_USER}&ApiKey=${NAMECHEAP_API_KEY}&UserName=${NAMECHEAP_USERNAME}&ClientIp=${CLIENT_IP}"

echo "=== current hosts ==="
curl -sS --max-time 30 "${BASE}?${AUTH}&Command=namecheap.domains.dns.getHosts&SLD=${SLD}&TLD=${TLD}" | tee /tmp/nc_get.xml | head -c 2000
echo

# Build setHosts for required names (@, www, sidms, scpms-app, scpms-api, office, docs, si-erp, si-erp-api)
# Namecheap uses HostName without zone suffix; @ for apex.
python3 <<PY
import urllib.parse, urllib.request, os, re, xml.etree.ElementTree as ET
origin=os.environ.get('ORIGIN','82.38.44.122')
# parse existing to preserve MX/TXT/CNAME we don't want to wipe
xml=open('/tmp/nc_get.xml').read()
# Namecheap responses often have default namespace
xml=re.sub(r'xmlns="[^"]+"','',xml)
root=ET.fromstring(xml)
hosts=[]
for h in root.findall('.//host'):
    hosts.append({
        'Name': h.attrib.get('Name') or h.attrib.get('HostName') or '',
        'Type': h.attrib.get('Type'),
        'Address': h.attrib.get('Address'),
        'MXPref': h.attrib.get('MXPref','10'),
        'TTL': h.attrib.get('TTL','300'),
    })
print('existing', len(hosts))
for h in hosts:
    print(h)

wanted={
    '@': origin,
    'www': origin,
    'sidms': origin,
    'scpms-app': origin,
    'scpms-api': origin,
    'office': origin,
    'docs': origin,
    'si-erp': origin,
    'si-erp-api': origin,
}
# drop A/AAAA/URL for those names; keep MX/TXT/other
keep=[]
for h in hosts:
    name=(h['Name'] or '').lower()
    typ=(h['Type'] or '').upper()
    if name in wanted and typ in ('A','AAAA','URL','CNAME','ALIAS'):
        continue
    keep.append(h)
# add our A records
for name,addr in wanted.items():
    keep.append({'Name':name,'Type':'A','Address':addr,'MXPref':'10','TTL':'300'})

params=[]
for i,h in enumerate(keep,1):
    params.append(('HostName%d'%i, h['Name']))
    params.append(('RecordType%d'%i, h['Type']))
    params.append(('Address%d'%i, h['Address']))
    params.append(('TTL%d'%i, h.get('TTL') or '300'))
    if (h['Type'] or '').upper()=='MX':
        params.append(('MXPref%d'%i, h.get('MXPref') or '10'))
open('/tmp/nc_set_params.txt','w').write(urllib.parse.urlencode(params))
print('will set', len(keep), 'records')
PY

QS=$(cat /tmp/nc_set_params.txt)
curl -sS --max-time 60 "${BASE}?${AUTH}&Command=namecheap.domains.dns.setHosts&SLD=${SLD}&TLD=${TLD}&${QS}" | tee /tmp/nc_set.xml
echo
grep -i 'IsSuccess\|Error\|Status' /tmp/nc_set.xml || true

echo "=== verify dig via registrar ==="
sleep 3
getent ahostsv4 scpms-app.sidms.online || true
