"""Premier PayFast (Pakistan IPG) client — ported from Desk (sandbox + live)."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from core.models import PayFastSettings

SUCCESS_CODES = {"00", "79", "000"}


class PayFastError(Exception):
    def __init__(self, message, payload=None):
        super().__init__(message)
        self.payload = payload or {}


def gateway_for(organization=None):
    """Platform SaaS gateway, or tenant gateway when organization has one ready."""
    if organization is not None:
        from core.models import TenantPayGateway

        try:
            gateway = organization.pay_gateway
        except TenantPayGateway.DoesNotExist:
            gateway = None
        if gateway is not None and gateway.ready:
            return gateway
    return PayFastSettings.load()


def secured_hash(*values, gateway=None):
    gateway = gateway or PayFastSettings.load()
    parts = [str(value) for value in values if value not in (None, "")]
    message = "+".join(parts).encode("ascii")
    key = gateway.hash_key.encode("ascii")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def success(payload):
    code = str(payload.get("status_code") or payload.get("code") or "")
    return code in SUCCESS_CODES


def message_of(payload):
    return str(
        payload.get("status_msg")
        or payload.get("message")
        or "PayFast could not complete the payment."
    )


def _json(raw):
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else {"result": value}


def _form(url, data):
    request = Request(
        url,
        data=urlencode(data).encode(),
        headers={
            "content-type": "application/x-www-form-urlencoded",
            "accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read().decode()
    except HTTPError as exc:
        raw = exc.read().decode(errors="replace")
        payload = _json(raw)
        raise PayFastError(
            message_of(payload) if payload else "PayFast rejected the request.", payload
        ) from exc
    except URLError as exc:
        raise PayFastError("PayFast could not be reached.") from exc
    payload = _json(raw)
    if payload is None:
        raise PayFastError("PayFast returned an unreadable response.")
    return payload


def gateway_origin(gateway=None):
    gateway = gateway or PayFastSettings.load()
    parsed = urlparse(gateway.api_base)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return "https://ipg1.apps.net.pk" if gateway.is_live else "https://ipguat.apps.net.pk"


def post_transaction_url(gateway=None):
    return f"{gateway_origin(gateway)}/Ecommerce/api/Transaction/PostTransaction"


def hosted_access_token(basket_id, amount, gateway=None):
    gateway = gateway or PayFastSettings.load()
    if not gateway.ready:
        mode = gateway.get_environment_display()
        raise PayFastError(f"Premier PayFast {mode} credentials are not set.")
    payload = _form(
        f"{gateway_origin(gateway)}/Ecommerce/api/Transaction/GetAccessToken",
        {
            "MERCHANT_ID": gateway.merchant_id,
            "SECURED_KEY": gateway.secured_key,
            "BASKET_ID": basket_id,
            "TXNAMT": amount,
            "CURRENCY_CODE": "PKR",
        },
    )
    token = payload.get("ACCESS_TOKEN") or payload.get("access_token")
    if not token:
        raise PayFastError("PayFast did not return an access token.", payload)
    return payload


def hosted_fields(
    *,
    token,
    merchant_name,
    basket_id,
    amount,
    mobile,
    email,
    description,
    success_url,
    failure_url,
    checkout_url,
    order_date,
    gateway=None,
):
    gateway = gateway or PayFastSettings.load()
    return {
        "MERCHANT_ID": gateway.merchant_id,
        "MERCHANT_NAME": merchant_name or "SIGBL ERP",
        "TOKEN": token,
        "PROCCODE": "00",
        "TXNAMT": amount,
        "CUSTOMER_MOBILE_NO": mobile,
        "CUSTOMER_EMAIL_ADDRESS": email,
        "SIGNATURE": secrets.token_hex(16),
        "VERSION": "SIGBL-ERP",
        "TXNDESC": description,
        "SUCCESS_URL": success_url,
        "FAILURE_URL": failure_url,
        "CHECKOUT_URL": checkout_url,
        "BASKET_ID": basket_id,
        "ORDER_DATE": order_date,
        "CURRENCY_CODE": "PKR",
        "TRAN_TYPE": "ECOMM_PURCHASE",
        "RECURRING_TXN": "FALSE",
    }


def callback_valid(basket_id, err_code, validation_hash, gateway=None):
    gateway = gateway or PayFastSettings.load()
    expected = hashlib.sha256(
        f"{basket_id}|{gateway.secured_key}|{gateway.merchant_id}|{err_code}".encode()
    ).hexdigest()
    given = str(validation_hash or "").strip().lower()
    if len(given) != len(expected):
        return False
    return hmac.compare_digest(expected, given)
