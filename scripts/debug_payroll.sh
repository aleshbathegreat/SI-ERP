#!/bin/bash
set -euo pipefail
TOKEN=$(curl -k -sS --max-time 15 --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"Admin@123"}' \
  https://si-erp-api.mushaz.com/api/auth/login/ | python3 -c 'import sys,json; print(json.load(sys.stdin).get("access",""))')
echo "token_len=${#TOKEN}"
for p in payroll/periods/ payroll/payslips/ payroll/structures/ payroll/periods; do
  code=$(curl -k -sS -o /tmp/r.json -w '%{http_code}' --max-time 15 \
    --resolve si-erp-api.mushaz.com:443:127.0.0.1 \
    -H "Authorization: Bearer $TOKEN" \
    "https://si-erp-api.mushaz.com/api/$p")
  echo "$p -> $code $(python3 -c 'import json;d=json.load(open(\"/tmp/r.json\"));print(type(d).__name__, (list(d)[:6] if isinstance(d,dict) else (\"len=\"+str(len(d)) if isinstance(d,list) else d)))' 2>/dev/null || head -c 160 /tmp/r.json)"
done
curl -k -sS -o /dev/null -w "page=%{http_code}\n" --max-time 15 --resolve si-erp.mushaz.com:443:127.0.0.1 https://si-erp.mushaz.com/payroll
docker logs jmc_api --since 30m 2>&1 | grep -iE 'payroll|Error|Traceback|Exception' | tail -25 || true
