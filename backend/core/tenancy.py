"""SaaS host → tenant resolution (platform subdomain + verified custom domains)."""

from __future__ import annotations

import json
import logging
import re
import secrets
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.conf import settings

logger = logging.getLogger(__name__)

_HOST_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[a-z0-9-]{1,63}(?<!-)(\.(?!-)[a-z0-9-]{1,63}(?<!-))*$"
)


def platform_root_domain() -> str:
    return (getattr(settings, "PLATFORM_ROOT_DOMAIN", "") or "").strip().lower().rstrip(".")


def platform_hosts() -> set[str]:
    raw = getattr(settings, "PLATFORM_HOSTS", "") or ""
    hosts = {h.strip().lower() for h in raw.split(",") if h.strip()}
    root = platform_root_domain()
    if root:
        hosts.add(root)
        hosts.add(f"www.{root}")
        hosts.add(f"app.{root}")
    hosts.update({"localhost", "127.0.0.1", "testserver"})
    return hosts


def normalize_host(host: str | None) -> str:
    if not host:
        return ""
    host = host.split(",")[0].strip().lower()
    if ":" in host and not host.startswith("["):
        host = host.rsplit(":", 1)[0]
    return host.rstrip(".")


def is_valid_hostname(host: str) -> bool:
    if not host or len(host) > 253:
        return False
    if host in ("localhost", "127.0.0.1"):
        return True
    return bool(_HOST_RE.match(host))


def subdomain_for(organization) -> str:
    root = platform_root_domain()
    if not root or not organization or not organization.code:
        return ""
    return f"{organization.code}.{root}"


def new_verify_token() -> str:
    return f"sigbl-verify-{secrets.token_urlsafe(18)}"


def resolve_organization(host: str | None):
    """Return Organization for Host, or None on platform apex / unknown."""
    from core.models import Organization

    host = normalize_host(host)
    if not host or host in platform_hosts():
        return None

    # Verified custom domain
    org = (
        Organization.objects.filter(
            custom_domain=host, custom_domain_verified=True, is_active=True
        )
        .select_related("package")
        .first()
    )
    if org:
        return org

    # Pending custom domain still maps for branding (not fully trusted for auth gates)
    org = (
        Organization.objects.filter(custom_domain=host, is_active=True)
        .select_related("package")
        .first()
    )
    if org:
        return org

    root = platform_root_domain()
    if root and host.endswith("." + root):
        code = host[: -(len(root) + 1)]
        if code and "." not in code:
            return (
                Organization.objects.filter(code=code, is_active=True)
                .select_related("package")
                .first()
            )
    return None


def host_allowed(host: str | None) -> bool:
    """True if Host is platform, subdomain of root, or a known tenant custom domain."""
    host = normalize_host(host)
    if not host:
        return False
    if host in platform_hosts():
        return True
    root = platform_root_domain()
    if root and (host == root or host.endswith("." + root)):
        return True
    from core.models import Organization

    return Organization.objects.filter(custom_domain=host, is_active=True).exists()


def dns_google_resolve(name: str, rtype: str = "CNAME") -> list[str]:
    """DNS lookup via Google DoH (no extra dependency)."""
    url = f"https://dns.google/resolve?name={name}&type={rtype}"
    try:
        req = Request(url, headers={"accept": "application/dns-json"})
        with urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
    except (URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        logger.info("DNS lookup failed for %s: %s", name, exc)
        return []
    answers = data.get("Answer") or []
    out = []
    for row in answers:
        if int(row.get("type") or 0) in (1, 5, 16, 28):  # A, CNAME, TXT, AAAA
            val = str(row.get("data") or "").strip().strip('"').rstrip(".")
            out.append(val.lower())
    return out


def verify_custom_domain(organization) -> tuple[bool, str]:
    """
    Pass if:
      - CNAME(custom) → {code}.{root} or root/app host, or
      - TXT _sigbl-challenge.{custom} contains domain_verify_token
    """
    domain = (organization.custom_domain or "").strip().lower()
    if not domain:
        return False, "No custom domain set"
    if not is_valid_hostname(domain):
        return False, "Invalid hostname"
    if domain in platform_hosts():
        return False, "Cannot use the platform hostname as a custom domain"

    token = (organization.domain_verify_token or "").lower()
    expected_cname_targets = set()
    sub = subdomain_for(organization)
    if sub:
        expected_cname_targets.add(sub)
    root = platform_root_domain()
    if root:
        expected_cname_targets.add(root)
        expected_cname_targets.add(f"app.{root}")
    expected_cname_targets |= platform_hosts()

    cnames = dns_google_resolve(domain, "CNAME")
    for cname in cnames:
        if cname in expected_cname_targets or any(
            cname.endswith("." + t) for t in expected_cname_targets if t
        ):
            return True, f"CNAME points to {cname}"

    txt_name = f"_sigbl-challenge.{domain}"
    txts = dns_google_resolve(txt_name, "TXT")
    for txt in txts:
        if token and token in txt.replace(" ", "").lower():
            return True, "TXT challenge matched"

    # A-record same as platform apex (shared ingress)
    if root:
        platform_ips = set(dns_google_resolve(root, "A")) | set(
            dns_google_resolve(f"app.{root}", "A")
        )
        domain_ips = set(dns_google_resolve(domain, "A"))
        if platform_ips and domain_ips & platform_ips:
            return True, "A record matches platform ingress"

    return (
        False,
        "DNS not ready. Add CNAME to "
        f"{sub or root or 'platform'} or TXT _sigbl-challenge.{domain} = {organization.domain_verify_token}",
    )


def _abs_media(file_field, request=None) -> str | None:
    if not file_field:
        return None
    try:
        url = file_field.url
    except ValueError:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if request is not None:
        return request.build_absolute_uri(url)
    from django.conf import settings

    base = getattr(settings, "PUBLIC_API_BASE", None) or getattr(
        settings, "FRONTEND_URL", ""
    )
    # Prefer API origin for /media when FRONTEND_URL is the Next app
    api = getattr(settings, "PUBLIC_MEDIA_BASE", "") or ""
    root = (api or base or "").rstrip("/")
    path = url if url.startswith("/") else f"/{url}"
    return f"{root}{path}" if root else path


def branding_payload(organization, request=None) -> dict:
    """Shared tenant brand dict for public + authenticated APIs."""
    if organization is None:
        logo = (
            "https://sigbl.com/wp-content/uploads/2024/04/cropped-sigbl_logo_cv-1.png"
        )
        return {
            "mode": "platform",
            "name": "SI-ERP",
            "code": None,
            "brand_name": "SI-ERP",
            "brand_tagline": "A-Symmetric ICT Solutions · Finance, HR & Payroll",
            "brand_primary_color": "#00A3C4",
            "brand_secondary_color": "#0B3D5C",
            "brand_logo_url": logo,
            "brand_logo_dark_url": logo,
            "brand_favicon_url": logo,
            "subdomain": None,
            "custom_domain": None,
            "custom_domain_verified": False,
        }
    return {
        "mode": "tenant",
        "id": organization.id,
        "name": organization.name,
        "code": organization.code,
        "brand_name": organization.brand_name or organization.name,
        "brand_tagline": organization.brand_tagline
        or "Finance, HR & Payroll",
        "brand_primary_color": organization.brand_primary_color or "#1B6A94",
        "brand_secondary_color": organization.brand_secondary_color or "#C45C26",
        "brand_logo_url": _abs_media(organization.brand_logo, request),
        "brand_logo_dark_url": _abs_media(organization.brand_logo_dark, request)
        or _abs_media(organization.brand_logo, request),
        "brand_favicon_url": _abs_media(organization.brand_favicon, request),
        "subdomain": subdomain_for(organization),
        "custom_domain": organization.custom_domain or None,
        "custom_domain_verified": bool(organization.custom_domain_verified),
    }


def public_branding(organization, request=None) -> dict:
    return branding_payload(organization, request=request)
