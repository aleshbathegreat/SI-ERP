#!/bin/bash
set -euo pipefail
JMC=/home/sidms/jmc

mkdir -p "$JMC/frontend/public/guide" "$JMC/frontend/.next"
cp /tmp/frontend-standalone.tgz "$JMC/"
rm -rf /tmp/guide_imgs && mkdir -p /tmp/guide_imgs
tar -xzf /tmp/guide-images.tgz -C /tmp/guide_imgs
cp -f /tmp/guide_imgs/*.png "$JMC/frontend/public/guide/" 2>/dev/null || true
# also if tarball contains guide/ subfolder
if [ -d /tmp/guide_imgs/guide ]; then
  cp -f /tmp/guide_imgs/guide/*.png "$JMC/frontend/public/guide/"
fi

cd "$JMC/frontend"
rm -rf .next && mkdir -p .next
tar -xzf "$JMC/frontend-standalone.tgz" -C "$JMC/frontend"
[ -d "$JMC/frontend/standalone" ] && mv "$JMC/frontend/standalone" "$JMC/frontend/.next/standalone"
[ -d "$JMC/frontend/static" ] && mv "$JMC/frontend/static" "$JMC/frontend/.next/static"

# Ensure guide images are inside standalone public if present
mkdir -p "$JMC/frontend/.next/standalone/public/guide"
cp -f "$JMC/frontend/public/guide/"*.png "$JMC/frontend/.next/standalone/public/guide/" 2>/dev/null || true
mkdir -p "$JMC/frontend/public/guide"

cd "$JMC"
docker compose build web
docker compose up -d --force-recreate web
sleep 5
curl -k -sS -o /dev/null -w "web=%{http_code}\n" --max-time 15 \
  --resolve si-erp.mushaz.com:443:127.0.0.1 https://si-erp.mushaz.com/login
curl -k -sS -o /dev/null -w "guide_img=%{http_code}\n" --max-time 15 \
  --resolve si-erp.mushaz.com:443:127.0.0.1 https://si-erp.mushaz.com/guide/dashboard.png
echo DONE
