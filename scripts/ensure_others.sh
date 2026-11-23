#!/bin/bash
# Read-only checks first; restart only clearly broken app containers (never Traefik).
set -e

echo "=== container status ==="
docker ps -a --format 'table {{.Names}}\t{{.Status}}' | sort

echo
echo "=== traefik routers ==="
curl -sS --max-time 5 http://127.0.0.1:9080/api/http/routers -o /tmp/tr.json
python3 <<'PY'
import json
d=json.load(open('/tmp/tr.json'))
for r in sorted(d, key=lambda x: x.get('name','')):
    if r.get('provider')=='docker' or 'docker' in r.get('name',''):
        print(f"{r['name']}\t{r.get('status')}\t{r.get('rule')}")
PY

echo
echo "=== local HTTPS via Traefik ==="
# Discover host rules from labels of running containers
python3 <<'PY'
import json,subprocess,re,urllib.request,ssl
ctx=ssl._create_unverified_context()
out=subprocess.check_output(['docker','ps','-q'], text=True).strip().split()
hosts=[]
for cid in out:
    labels=json.loads(subprocess.check_output(['docker','inspect',cid,'--format','{{json .Config.Labels}}'], text=True) or '{}')
    if labels.get('traefik.enable')!='true':
        continue
    name=subprocess.check_output(['docker','inspect',cid,'--format','{{.Name}}'], text=True).strip().lstrip('/')
    for k,v in labels.items():
        if k.endswith('.rule') and 'Host(' in v:
            for m in re.findall(r"Host\(`([^`]+)`\)", v):
                hosts.append((name,m))
print('discovered', len(hosts), 'hosts')
for name,h in sorted(set(hosts), key=lambda x: x[1]):
    # resolve via 127.0.0.1
    import subprocess as sp
    r=sp.run(['curl','-k','-sS','-o','/dev/null','-w','%{http_code}','--max-time','8','--resolve',f'{h}:443:127.0.0.1',f'https://{h}/'], capture_output=True, text=True)
    code=r.stdout.strip() or 'fail'
    print(f'{h}\t{code}\t({name})')
PY

echo
echo "=== critical stack health (scpms/sidms/zeehealth/traefik) ==="
for n in traefik scpms-frontend-1 scpms-backend-1 scpms-postgres-1 scpms-redis-1 scpms-rabbitmq-1 sidms-app_server sidms-landing zeehealth-admin-1 zeehealth-api-1; do
  st=$(docker inspect -f '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}nohealth{{end}}' "$n" 2>/dev/null || echo missing)
  echo "$n -> $st"
done
