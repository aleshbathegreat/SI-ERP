#!/bin/bash
set -e
echo "=== functional smoke (no restarts) ==="
while IFS='|' read -r h p; do
  code=$(curl -k -sS -o /dev/null -w "%{http_code}" --max-time 8 --resolve "${h}:443:127.0.0.1" "https://${h}${p}" || echo fail)
  echo "${h}${p} -> ${code}"
done <<'EOF'
scpms-app.sidms.online|/
scpms-api.sidms.online|/admin/
sidms.online|/
sidms.sidms.online|/
zeehealth-admin.zeeshad.com|/
office.sidms.online|/
docs.sidms.online|/
EOF
echo
echo -n "running non-jmc: "
docker ps --format '{{.Names}}' | grep -vc '^jmc_' || true
echo -n "jmc running: "
docker ps --format '{{.Names}}' | grep -c '^jmc_' || true
echo -n "traefik: "
docker inspect -f '{{.State.Status}}' traefik
