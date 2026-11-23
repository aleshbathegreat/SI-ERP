#!/bin/bash
set -euo pipefail
cd /home/sidms/jmc
# Extract frontend build shipped as tarball
tar -xzf /home/sidms/jmc/frontend-standalone.tgz -C /home/sidms/jmc/frontend
docker compose build web
docker compose up -d web
sleep 5
docker ps --filter name=jmc_web --format '{{.Names}} {{.Status}}'
docker exec jmc_web sh -c "grep -Rao 'si-erp-api[a-z0-9.-]*\|127.0.0.1:8000' /app/.next/static 2>/dev/null | sort -u | head -20"
curl -k -sS -o /dev/null -w "web=%{http_code}\n" --max-time 15 --resolve si-erp.mushaz.com:443:127.0.0.1 https://si-erp.mushaz.com/login
curl -sS -o /dev/null -w "public_login=%{http_code}\n" --max-time 20 https://si-erp.mushaz.com/login || true
echo DONE
