#!/bin/bash
set -euo pipefail
API="https://si-erp-api.mushaz.com"
WEB="https://si-erp.mushaz.com"

echo "=== public health ==="
curl -sS -o /dev/null -w "api_health=%{http_code}\n" --max-time 20 "$API/api/health/"
curl -sS -o /dev/null -w "web=%{http_code}\n" --max-time 20 "$WEB/"

echo
echo "=== login attempts ==="
python3 <<'PY'
import json, urllib.request, urllib.error

API = "https://si-erp-api.mushaz.com"
users = [
    ("admin", "Admin@123"),
    ("fin.mgr", "Fin@12345"),
    ("hr.mgr", "Hr@12345"),
    ("pay.officer", "Pay@12345"),
    ("approver1", "App@12345"),
    ("initiator1", "Init@12345"),
    ("ess.user", "Ess@12345"),
    ("auditor1", "Aud@12345"),
    ("admin", "WrongPass"),  # expect fail
]

# discover login path candidates
candidates = [
    "/api/auth/login/",
    "/api/token/",
    "/api/accounts/login/",
    "/api/auth/jwt/create/",
    "/api/login/",
]

login_path = None
# probe with admin on each
body = json.dumps({"username": "admin", "password": "Admin@123"}).encode()
for path in candidates:
    req = urllib.request.Request(
        API + path,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            raw = r.read().decode()
            code = r.status
            data = json.loads(raw) if raw else {}
            if code == 200 and (data.get("access") or data.get("token") or data.get("refresh") or data.get("user")):
                login_path = path
                print(f"endpoint {path} OK")
                break
            print(f"endpoint {path} -> {code} keys={list(data)[:8]}")
            if code < 500:
                login_path = path
                break
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        print(f"endpoint {path} -> HTTP {e.code} {raw[:120]}")
        if e.code in (400, 401, 403) and path.endswith("login/") or "token" in path:
            # path exists
            login_path = login_path or path
    except Exception as e:
        print(f"endpoint {path} -> {e}")

if not login_path:
    # fallback: ask openapi or urls via container
    print("NO_LOGIN_PATH_FROM_PUBLIC — trying inside container")
    raise SystemExit(2)

print("using", login_path)
ok = 0
for user, password in users:
    payload = json.dumps({"username": user, "password": password}).encode()
    req = urllib.request.Request(
        API + login_path,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    expect_ok = password != "WrongPass"
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            data = json.loads(r.read().decode())
            token = data.get("access") or data.get("token") or ""
            if expect_ok and (token or data.get("user") or data.get("refresh")):
                print(f"OK   {user:12} -> {r.status} token={bool(token)}")
                ok += 1
            elif not expect_ok:
                print(f"FAIL {user:12} unexpected success")
            else:
                print(f"BAD  {user:12} -> {r.status} body_keys={list(data)[:6]}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")[:160]
        if not expect_ok and e.code in (400, 401):
            print(f"OK   {user:12} rejected as expected ({e.code})")
            ok += 1
        else:
            print(f"FAIL {user:12} HTTP {e.code} {raw}")
    except Exception as e:
        print(f"FAIL {user:12} {e}")

print(f"\npassed {ok}/{len(users)}")
PY
