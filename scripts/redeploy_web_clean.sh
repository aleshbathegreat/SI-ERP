#!/bin/bash
set -euo pipefail
cd /home/sidms/jmc/frontend
rm -rf .next
mkdir -p .next
tar -xzf /home/sidms/jmc/frontend-standalone.tgz -C /home/sidms/jmc/frontend
# tarball has .next/standalone and .next/static
ls -la .next | head
grep -Rao 'si-erp-api[a-z0-9.-]*\|127.0.0.1:8000' .next/static 2>/dev/null | sort -u || true
cd /home/sidms/jmc
docker compose build web --no-cache
docker compose up -d --force-recreate web
sleep 6
echo "=== in image ==="
docker exec jmc_web sh -c "grep -Rao 'si-erp-api[a-z0-9.-]*\|127.0.0.1:8000' /app/.next/static 2>/dev/null | sort -u"
curl -k -sS -o /dev/null -w "login=%{http_code}\n" --max-time 15 --resolve si-erp.mushaz.com:443:127.0.0.1 https://si-erp.mushaz.com/login
# fetch login HTML and see which chunk / api host referenced
curl -k -sS --max-time 15 --resolve si-erp.mushaz.com:443:127.0.0.1 https://si-erp.mushaz.com/login | grep -oE 'si-erp-api[a-z0-9.-]+|/_next/static/chunks/[a-z0-9._-]+\.js' | sort -u | head -30
echo DONE
