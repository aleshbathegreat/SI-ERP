#!/bin/bash
set -e
echo "=== API health paths ==="
curl -k -sS -o /dev/null -w "scpms-api /api/ : %{http_code}\n" --max-time 8 --resolve scpms-api.sidms.online:443:127.0.0.1 https://scpms-api.sidms.online/api/ || true
curl -k -sS -o /dev/null -w "scpms-api /admin/ : %{http_code}\n" --max-time 8 --resolve scpms-api.sidms.online:443:127.0.0.1 https://scpms-api.sidms.online/admin/ || true
curl -k -sS -o /dev/null -w "zeehealth-apis / : %{http_code}\n" --max-time 8 --resolve zeehealth-apis.zeeshad.com:443:127.0.0.1 https://zeehealth-apis.zeeshad.com/ || true
curl -k -sS -o /dev/null -w "zeehealth-apis /api/v1/health/ : %{http_code}\n" --max-time 8 --resolve zeehealth-apis.zeeshad.com:443:127.0.0.1 https://zeehealth-apis.zeeshad.com/api/v1/health/ || true
curl -k -sS -o /dev/null -w "docs / : %{http_code}\n" --max-time 8 --resolve docs.sidms.online:443:127.0.0.1 https://docs.sidms.online/ || true

echo
echo "=== internal healthchecks failing why ==="
for n in sidms-postgres_db sidms-redis_db sidms-rabbitmq_server zeehealth-postgres-1 zeehealth-redis-1 zeehealth-api-1 docssidms; do
  echo "--- $n ---"
  docker inspect "$n" --format 'status={{.State.Status}} health={{if .State.Health}}{{.State.Health.Status}}{{end}}' 2>/dev/null || echo missing
  docker inspect "$n" --format '{{range .State.Health.Log}}{{.ExitCode}} {{.Output}}{{end}}' 2>/dev/null | tail -c 400
  echo
done

echo
echo "=== can sidms app talk to db? (via app logs last errors) ==="
docker logs sidms-app_server --since 30m 2>&1 | grep -iE 'error|exception|refused|timeout' | tail -8 || echo none
docker logs zeehealth-api-1 --since 30m 2>&1 | grep -iE 'error|exception|refused|timeout' | tail -8 || echo none
docker logs scpms-backend-1 --since 30m 2>&1 | grep -iE 'error|exception|refused|timeout' | tail -5 || echo none

echo
echo "=== exec quick probes inside deps ==="
docker exec sidms-postgres_db pg_isready 2>&1 || true
docker exec sidms-redis_db redis-cli ping 2>&1 || true
docker exec zeehealth-postgres-1 pg_isready 2>&1 || true
docker exec zeehealth-redis-1 redis-cli ping 2>&1 || true
docker exec scpms-postgres-1 pg_isready 2>&1 || true
