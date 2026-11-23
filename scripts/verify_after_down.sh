#!/bin/bash
set -e
curl -sS http://127.0.0.1:9080/api/http/routers -o /tmp/tr.json
python3 <<'PY'
import json
d=json.load(open('/tmp/tr.json'))
print('router_count', len(d))
for r in sorted(d, key=lambda x: x['name']):
    print(r['name'], r.get('status'), r.get('rule'))
PY
echo
for h in scpms-app.sidms.online scpms-api.sidms.online; do
  code=$(curl -k -sS -o /dev/null -w "%{http_code}" --max-time 8 --resolve ${h}:443:127.0.0.1 "https://${h}/" || echo fail)
  echo "$h $code"
done
echo
docker ps --filter name=jmc_ --format '{{.Names}}' | grep . && echo 'WARN jmc still present' || echo 'jmc: none'
docker ps --filter name=^traefik$ --format 'traefik {{.Status}}'
