#!/bin/bash
set -e
echo "=== bash history around docker/traefik/jmc/dns ==="
grep -nE 'traefik|compose|ufw|cloudflare|dns|jmc|scpms|80|443|acme' /home/sidms/.bash_history 2>/dev/null | tail -60 || true

echo
echo "=== docker nat 80/443 mappings ==="
sudo iptables -t nat -L PREROUTING -n -v | head -5
sudo iptables -t nat -L DOCKER -n -v --line-numbers
echo
sudo iptables -L DOCKER-USER -n -v 2>/dev/null || true
sudo iptables -L FORWARD -n -v | head -15

echo
echo "=== traefik publish inspect ==="
docker inspect traefik --format 'Ports={{json .NetworkSettings.Ports}} NetworkMode={{.HostConfig.NetworkMode}} Dns={{json .HostConfig.Dns}} Restart={{.RestartCount}} Started={{.State.StartedAt}}'

echo
echo "=== acme.json size / cert count / mtime ==="
ls -la /home/sidms/traefik/acme.json
python3 <<'PY'
import json
d=json.load(open('/home/sidms/traefik/acme.json'))
certs=d.get('cloudflare',{}).get('Certificates')
print('Certificates type', type(certs).__name__, 'len', (len(certs) if isinstance(certs,list) else certs))
# account present?
acc=d.get('cloudflare',{}).get('Account')
print('Account keys', list(acc.keys()) if isinstance(acc,dict) else acc)
PY

echo
echo "=== TLS cert currently served locally for sidms/scpms ==="
for h in sidms.sidms.online scpms-app.sidms.online; do
  echo "--- $h ---"
  echo | openssl s_client -connect 127.0.0.1:443 -servername "$h" 2>/dev/null | openssl x509 -noout -subject -issuer -dates 2>/dev/null || echo 'no cert'
done

echo
echo "=== docker events create/start/die last 24h (apps/traefik) ==="
docker events --since 24h --until 0s --filter type=container --format '{{.Time}} {{.Action}} {{.Actor.Attributes.name}}' 2>/dev/null \
  | grep -iE 'traefik|scpms-frontend|scpms-backend|sidms-app|jmc_|network' | grep -vE 'exec_' | tail -80 || true
