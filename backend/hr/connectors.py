"""Attendance device connector catalog + package entitlement helpers.

Connectors cover common market devices that integrate via ADMS/push,
vendor cloud/REST APIs, ISAPI, or generic webhook/CSV. Full proprietary
SDK pull is adapter-ready; push ingest and CSV work out of the box.
"""

from __future__ import annotations

from typing import Any

# Connection modes supported by the platform.
MODE_PUSH = "push_webhook"
MODE_PULL = "pull_tcp"
MODE_CLOUD = "cloud_api"
MODE_CSV = "csv_import"

WEBHOOK_PATH = "/api/hr/attendance/device-sync/"

SAMPLE_PUSH_PAYLOAD = {
    "device_id": "GATE-01",
    "connector_key": "generic_webhook",
    "punches": [
        {
            "employee_code": "EMP-0001",
            "work_date": "2026-10-29",
            "check_in": "09:02:00",
            "check_out": None,
            "status": "present",
        }
    ],
}


def _caps(*modes: str, live_pull: bool = False) -> dict[str, Any]:
    return {
        "push": MODE_PUSH in modes,
        "pull": MODE_PULL in modes,
        "cloud": MODE_CLOUD in modes,
        "csv": MODE_CSV in modes,
        "live_pull_agent": live_pull,
        "webhook_auth": MODE_PUSH in modes,
    }


def _steps_push(vendor: str) -> list[str]:
    return [
        f"Entitle the {vendor} connector on your subscription package.",
        "Create a device under Attendance → Devices (choose this connector, mode = push).",
        "Copy the device webhook secret from Test connection.",
        f"Configure the terminal / middleware to POST JSON punches to {WEBHOOK_PATH}.",
        "Send header X-Device-Secret with the device secret (or use tenant auth).",
        "Verify punches appear on Today board / Records with source=device.",
    ]


def _steps_cloud(vendor: str) -> list[str]:
    return [
        f"Entitle the {vendor} connector on your package.",
        "Add a device with connection mode = cloud_api; set host/base URL and API token.",
        "Run Test connection to validate config.",
        "Use Pull sync (or schedule a pull agent) to fetch transactions.",
        "Map vendor user IDs to SI-ERP employee_code where required.",
    ]


def _steps_csv() -> list[str]:
    return [
        "Entitle CSV connector and add a CSV device (or reuse generic_csv).",
        "Export punches from your legacy software as UTF-8 CSV.",
        "Columns: employee_code, work_date, check_in, check_out (optional status).",
        "Open the device → Import CSV (or Devices list actions).",
        "Reconcile the day if auto-absent is enabled.",
    ]


CONNECTOR_CATALOG: list[dict[str, Any]] = [
    {
        "key": "zkteco_adms",
        "vendor": "ZKTeco",
        "name": "ZKTeco ADMS / Push SDK",
        "models": "K40, K50, MB360, SpeedFace, uFace, inBio, ProFace X, iFace",
        "modes": [MODE_PUSH, MODE_PULL],
        "default_port": 4370,
        "protocol": "ADMS / ZK push",
        "tier": "standard",
        "category": "biometric",
        "docs": "Device pushes punches to SI-ERP webhook; optional TCP pull via agent.",
        "capabilities": _caps(MODE_PUSH, MODE_PULL, live_pull=True),
        "setup_steps": _steps_push("ZKTeco ADMS"),
        "status": "ga",
    },
    {
        "key": "zkteco_biotime",
        "vendor": "ZKTeco",
        "name": "ZKTeco BioTime / ZKBio CVSecurity",
        "models": "BioTime 8, ZKBioSecurity, ZKBio CVSecurity",
        "modes": [MODE_CLOUD, MODE_PUSH],
        "default_port": 8088,
        "protocol": "BioTime REST / webhook",
        "tier": "professional",
        "category": "time_attendance_suite",
        "docs": "Pull transactions from BioTime API or receive push events.",
        "capabilities": _caps(MODE_CLOUD, MODE_PUSH, live_pull=True),
        "setup_steps": _steps_cloud("ZKTeco BioTime"),
        "status": "ga",
    },
    {
        "key": "hikvision_isapi",
        "vendor": "Hikvision",
        "name": "Hikvision ISAPI Access",
        "models": "DS-K1T, MinMoe, Face Pro, Access Controllers",
        "modes": [MODE_CLOUD, MODE_PUSH],
        "default_port": 443,
        "protocol": "ISAPI / HTTPS",
        "tier": "professional",
        "category": "access_control",
        "docs": "Event subscription or periodic event search via ISAPI.",
        "capabilities": _caps(MODE_CLOUD, MODE_PUSH, live_pull=True),
        "setup_steps": _steps_cloud("Hikvision ISAPI"),
        "status": "ga",
    },
    {
        "key": "dahua_dss",
        "vendor": "Dahua",
        "name": "Dahua DSS / Access Control",
        "models": "ASI1201, ASI7213, DSS Express / Pro",
        "modes": [MODE_CLOUD, MODE_PUSH],
        "default_port": 443,
        "protocol": "HTTP API / DSS",
        "tier": "professional",
        "category": "access_control",
        "docs": "DSS event push or API pull for access events.",
        "capabilities": _caps(MODE_CLOUD, MODE_PUSH, live_pull=True),
        "setup_steps": _steps_cloud("Dahua DSS"),
        "status": "ga",
    },
    {
        "key": "anviz_crosschex",
        "vendor": "Anviz",
        "name": "Anviz CrossChex / Device API",
        "models": "W1 Pro, C2 Pro, FaceDeep, VF30",
        "modes": [MODE_PUSH, MODE_PULL, MODE_CLOUD],
        "default_port": 5010,
        "protocol": "CrossChex Cloud / TCP",
        "tier": "standard",
        "category": "biometric",
        "docs": "CrossChex cloud sync or device TCP protocol.",
        "capabilities": _caps(MODE_PUSH, MODE_PULL, MODE_CLOUD, live_pull=True),
        "setup_steps": _steps_push("Anviz"),
        "status": "ga",
    },
    {
        "key": "suprema_biostar",
        "vendor": "Suprema",
        "name": "Suprema BioStar 2",
        "models": "BioEntry W2, FaceStation F2, XPass 2, BioStation",
        "modes": [MODE_CLOUD, MODE_PUSH],
        "default_port": 443,
        "protocol": "BioStar 2 REST",
        "tier": "enterprise",
        "category": "access_control",
        "docs": "BioStar 2 API event search / webhook.",
        "capabilities": _caps(MODE_CLOUD, MODE_PUSH, live_pull=True),
        "setup_steps": _steps_cloud("Suprema BioStar 2"),
        "status": "ga",
    },
    {
        "key": "essl_biomax",
        "vendor": "eSSL",
        "name": "eSSL / Biomax",
        "models": "X990, K30, Face ID series, Biomax N-Series",
        "modes": [MODE_PUSH, MODE_PULL],
        "default_port": 4370,
        "protocol": "ADMS-compatible / eSSL push",
        "tier": "standard",
        "category": "biometric",
        "docs": "ADMS-style push (ZK-compatible firmware) or CSV.",
        "capabilities": _caps(MODE_PUSH, MODE_PULL, live_pull=True),
        "setup_steps": _steps_push("eSSL"),
        "status": "ga",
    },
    {
        "key": "realand",
        "vendor": "Realand",
        "name": "Realand Attendance",
        "models": "A-C071, F30, FacePro series",
        "modes": [MODE_PUSH, MODE_PULL],
        "default_port": 5005,
        "protocol": "Realand TCP / push",
        "tier": "standard",
        "category": "biometric",
        "docs": "Device push webhook or TCP pull adapter.",
        "capabilities": _caps(MODE_PUSH, MODE_PULL, live_pull=True),
        "setup_steps": _steps_push("Realand"),
        "status": "ga",
    },
    {
        "key": "idemia_morpho",
        "vendor": "IDEMIA",
        "name": "IDEMIA Morpho / Sigma",
        "models": "Sigma Lite, Sigma Wide, VisionPass",
        "modes": [MODE_CLOUD, MODE_PUSH],
        "default_port": 443,
        "protocol": "MorphoManager / REST",
        "tier": "enterprise",
        "category": "access_control",
        "docs": "Enterprise access events via MorphoManager or webhook.",
        "capabilities": _caps(MODE_CLOUD, MODE_PUSH, live_pull=True),
        "setup_steps": _steps_cloud("IDEMIA"),
        "status": "ga",
    },
    {
        "key": "timetec_biotime",
        "vendor": "TimeTec / FingerTec",
        "name": "FingerTec / TimeTec Cloud",
        "models": "AC100, Face ID 5, TimeTec TA",
        "modes": [MODE_CLOUD, MODE_PUSH],
        "default_port": 443,
        "protocol": "TimeTec Cloud API",
        "tier": "professional",
        "category": "time_attendance_suite",
        "docs": "Cloud API pull of clocking transactions.",
        "capabilities": _caps(MODE_CLOUD, MODE_PUSH, live_pull=True),
        "setup_steps": _steps_cloud("TimeTec"),
        "status": "ga",
    },
    {
        "key": "generic_webhook",
        "vendor": "Generic",
        "name": "Generic HTTP webhook",
        "models": "Any device/middleware that can POST JSON punches",
        "modes": [MODE_PUSH],
        "default_port": 443,
        "protocol": "HTTPS JSON",
        "tier": "standard",
        "category": "middleware",
        "docs": f"POST punches to {WEBHOOK_PATH} with X-Device-Secret.",
        "capabilities": _caps(MODE_PUSH),
        "setup_steps": _steps_push("Generic webhook"),
        "status": "ga",
        "sample_payload": SAMPLE_PUSH_PAYLOAD,
    },
    {
        "key": "generic_csv",
        "vendor": "Generic",
        "name": "CSV / Excel import",
        "models": "Exports from any attendance software",
        "modes": [MODE_CSV],
        "default_port": None,
        "protocol": "CSV upload",
        "tier": "standard",
        "category": "import",
        "docs": "Upload punch CSV (employee_code, work_date, check_in, check_out).",
        "capabilities": _caps(MODE_CSV),
        "setup_steps": _steps_csv(),
        "status": "ga",
        "sample_csv_header": "employee_code,work_date,check_in,check_out,status",
    },
]

CONNECTOR_BY_KEY = {c["key"]: c for c in CONNECTOR_CATALOG}
ALL_CONNECTOR_KEYS = [c["key"] for c in CONNECTOR_CATALOG]


def catalog_public(entitled_keys: list[str] | None = None) -> list[dict[str, Any]]:
    """Catalog with entitlement flags for the current org package."""
    entitled = set(entitled_keys) if entitled_keys is not None else set(ALL_CONNECTOR_KEYS)
    out = []
    for c in CONNECTOR_CATALOG:
        item = dict(c)
        item["entitled"] = c["key"] in entitled
        item["webhook_path"] = WEBHOOK_PATH
        if "sample_payload" not in item and MODE_PUSH in c.get("modes", []):
            payload = dict(SAMPLE_PUSH_PAYLOAD)
            payload["connector_key"] = c["key"]
            item["sample_payload"] = payload
        out.append(item)
    return out


def catalog_with_health(org, entitled_keys: list[str] | None = None) -> dict[str, Any]:
    """Enterprise catalog: entitlement + per-connector device health/usage."""
    from hr.models import AttendanceDevice

    connectors = catalog_public(entitled_keys)
    usage: dict[str, list] = {}
    if org:
        for d in AttendanceDevice.objects.filter(
            organization=org, is_deleted=False
        ).only(
            "id",
            "device_id",
            "connector_key",
            "is_active",
            "last_sync_at",
            "last_sync_status",
            "last_sync_message",
            "connection_mode",
            "location",
        ):
            usage.setdefault(d.connector_key, []).append(d)

    enriched = []
    healthy = degraded = idle = 0
    for c in connectors:
        devices = usage.get(c["key"], [])
        active = [d for d in devices if d.is_active]
        err = [d for d in devices if d.last_sync_status == "error"]
        ok = [d for d in devices if d.last_sync_status == "ok"]
        last_at = None
        for d in devices:
            if d.last_sync_at and (last_at is None or d.last_sync_at > last_at):
                last_at = d.last_sync_at
        if err:
            health = "error"
            degraded += 1
        elif ok:
            health = "ok"
            healthy += 1
        elif devices:
            health = "idle"
            idle += 1
        else:
            health = "unused"
        item = dict(c)
        item["usage"] = {
            "devices": len(devices),
            "active": len(active),
            "errors": len(err),
            "ok": len(ok),
            "last_sync_at": last_at.isoformat() if last_at else None,
            "health": health,
            "device_ids": [d.device_id for d in devices[:8]],
        }
        enriched.append(item)

    entitled_n = sum(1 for c in enriched if c.get("entitled"))
    return {
        "connectors": enriched,
        "summary": {
            "catalog_total": len(enriched),
            "entitled": entitled_n,
            "locked": len(enriched) - entitled_n,
            "connectors_in_use": sum(1 for c in enriched if c["usage"]["devices"] > 0),
            "healthy": healthy,
            "degraded": degraded,
            "idle": idle,
        },
        "integration": {
            "webhook_path": WEBHOOK_PATH,
            "webhook_auth_header": "X-Device-Secret",
            "sample_payload": SAMPLE_PUSH_PAYLOAD,
            "csv_header": "employee_code,work_date,check_in,check_out,status",
        },
    }


def package_connector_keys(package) -> list[str]:
    """Allowed connector keys for a subscription package.

    Empty list on package means none (devices locked) when module is present
    callers should still require hr.attendance_devices. Special value ["*"]
    or missing field defaults to all connectors when devices module entitled.
    """
    if package is None:
        return list(ALL_CONNECTOR_KEYS)
    raw = getattr(package, "attendance_connectors", None)
    if raw is None:
        return list(ALL_CONNECTOR_KEYS)
    if not isinstance(raw, list):
        return []
    if "*" in raw or "all" in raw:
        return list(ALL_CONNECTOR_KEYS)
    return [k for k in raw if k in CONNECTOR_BY_KEY]


def package_max_devices(package) -> int | None:
    """Max devices; None = unlimited (legacy / no package)."""
    if package is None:
        return None
    val = getattr(package, "max_attendance_devices", None)
    if val is None:
        return None
    return int(val)


def org_device_entitlement(org) -> dict[str, Any]:
    from accounts.rbac import org_entitled_modules

    entitled_mods = org_entitled_modules(org)
    devices_module_ok = entitled_mods is None or "hr.attendance_devices" in entitled_mods
    pkg = getattr(org, "package", None) if org else None
    connectors = package_connector_keys(pkg) if devices_module_ok else []
    max_dev = package_max_devices(pkg) if devices_module_ok else 0
    return {
        "module_enabled": devices_module_ok,
        "connectors": connectors,
        "max_devices": max_dev,
    }
