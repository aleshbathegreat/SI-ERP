#!/bin/bash
cd /home/sidms/jmc || exit 1
docker compose ps
echo "---"
docker exec jmc_api python -c "import urllib.request; print('api_local', urllib.request.urlopen('http://127.0.0.1:8000/api/health/').read().decode())"
curl -k -sS -o /dev/null -w "api_https:%{http_code}\n" --resolve si-erp-api.sidms.online:443:127.0.0.1 https://si-erp-api.sidms.online/api/health/
curl -k -sS -o /dev/null -w "web_https:%{http_code}\n" --resolve si-erp.sidms.online:443:127.0.0.1 https://si-erp.sidms.online/login
curl -sS -o /dev/null -w "api_public:%{http_code}\n" https://si-erp-api.sidms.online/api/health/ || true
curl -sS -o /dev/null -w "web_public:%{http_code}\n" https://si-erp.sidms.online/login || true
