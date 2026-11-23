#!/bin/bash
set -e
docker exec jmc_web sh -c "grep -Rao '127.0.0.1:8000\|si-erp-api[a-z0-9.-]*\|sidms.online\|mushaz.com' /app/.next/static 2>/dev/null | sort -u | head -50"
echo "---"
ls /home/sidms/jmc/frontend | head -20
command -v node; command -v npm; node -v 2>/dev/null || true
