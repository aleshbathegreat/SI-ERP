#!/bin/bash
set -euo pipefail
echo "=== login via Traefik localhost (bypass Cloudflare) ==="
python3 <<'PY'
import json, urllib.request, urllib.error, ssl

ctx = ssl._create_unverified_context()
API = "https://si-erp-api.mushaz.com"
PATH = "/api/auth/login/"
users = [
    ("admin", "Admin@123", True),
    ("fin.mgr", "Fin@12345", True),
    ("hr.mgr", "Hr@12345", True),
    ("pay.officer", "Pay@12345", True),
    ("approver1", "App@12345", True),
    ("initiator1", "Init@12345", True),
    ("ess.user", "Ess@12345", True),
    ("auditor1", "Aud@12345", True),
    ("admin", "WrongPass", False),
]

class Resolver(urllib.request.HTTPSHandler):
    pass

# Use curl subprocess for --resolve reliability
import subprocess, shlex
ok = 0
for user, password, expect_ok in users:
    payload = json.dumps({"username": user, "password": password})
    cmd = [
        "curl", "-k", "-sS", "-o", "/tmp/login_out.json", "-w", "%{http_code}",
        "--max-time", "20",
        "--resolve", "si-erp-api.mushaz.com:443:127.0.0.1",
        "-H", "Content-Type: application/json",
        "-H", "Accept: application/json",
        "-X", "POST",
        f"{API}{PATH}",
        "-d", payload,
    ]
    code = subprocess.check_output(cmd, text=True).strip()
    try:
        data = json.load(open("/tmp/login_out.json"))
    except Exception:
        data = {"raw": open("/tmp/login_out.json").read()[:200]}
    has_token = bool(data.get("access") or data.get("token") or data.get("refresh"))
    if expect_ok and code == "200" and has_token:
        uname = (data.get("user") or {}).get("username") or user
        print(f"OK   {user:12} http={code} access=yes user={uname}")
        ok += 1
    elif not expect_ok and code in ("400", "401"):
        print(f"OK   {user:12} rejected as expected http={code}")
        ok += 1
    else:
        print(f"FAIL {user:12} http={code} body={json.dumps(data)[:180]}")

print(f"\npassed {ok}/{len(users)}")

# also direct to container network
print("\n=== direct container login (admin) ===")
import os
# get api IP on jmc or web network
cip = subprocess.check_output(
    ["docker", "inspect", "-f", "{{range.NetworkSettings.Networks}}{{.IPAddress}} {{end}}", "jmc_api"],
    text=True,
).strip().split()[0]
print("jmc_api", cip)
payload = json.dumps({"username": "admin", "password": "Admin@123"})
cmd = [
    "curl", "-sS", "-o", "/tmp/login_direct.json", "-w", "%{http_code}",
    "--max-time", "15",
    "-H", "Content-Type: application/json",
    "-X", "POST",
    f"http://{cip}:8000/api/auth/login/",
    "-d", payload,
]
code = subprocess.check_output(cmd, text=True).strip()
data = json.load(open("/tmp/login_direct.json"))
print("direct", code, "access", bool(data.get("access")), "user", (data.get("user") or {}).get("username"))
raise SystemExit(0 if ok == len(users) else 1)
PY
