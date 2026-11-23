#!/bin/bash
set -euo pipefail
JMC=/home/sidms/jmc
cp /tmp/frontend-standalone.tgz "$JMC/"
cd "$JMC/frontend"
rm -rf .next/standalone .next/static standalone static
mkdir -p .next
tar -xzf "$JMC/frontend-standalone.tgz" -C "$JMC/frontend"
[ -d standalone ] && mv standalone .next/standalone
[ -d static ] && mv static .next/static
mkdir -p .next/standalone/.next
rm -rf .next/standalone/.next/static
cp -a .next/static .next/standalone/.next/static
cd "$JMC"
docker compose build web
docker compose up -d --force-recreate web
sleep 6
curl -k -sS -o /dev/null -w "ess_payslips=%{http_code}\n" --max-time 20 \
  --resolve si-erp.mushaz.com:443:127.0.0.1 https://si-erp.mushaz.com/ess/payslips
echo DONE
