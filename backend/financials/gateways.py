"""Payment and e-invoicing gateway clients: Moyasar and ZATCA Fatoora.

Moyasar — official API contract (docs.moyasar.com):
- Base URL ``https://api.moyasar.com/v1`` — HTTPS only.
- HTTP Basic auth: the secret key is the username, the password stays empty.
- Amounts are integers in the smallest currency unit (halalas for SAR).
- Refunds: ``POST /payments/:id/refund`` with optional ``amount``; omitting
  it refunds the full payment.

ZATCA Fatoora — e-invoicing portal API (Accept-Version: V2):
- ``POST /compliance`` with the base64 CSR and the portal ``OTP`` header
  returns the compliance CSID (``binarySecurityToken``), its ``secret`` and
  a ``requestID``.
- ``POST /production/csids`` (Basic auth = compliance CSID/secret) trades
  the ``compliance_request_id`` for the production CSID.
- ``POST /invoices/reporting/single`` reports signed simplified invoices;
  ``POST /invoices/clearance/single`` clears standard invoices (ZATCA
  applies the stamp and returns the cleared XML). Both take
  ``{invoiceHash, uuid, invoice(base64)}`` under Basic auth.
"""

from decimal import Decimal

import httpx
from django.conf import settings


class MoyasarError(Exception):
    """A non-2xx response from the Moyasar API."""

    def __init__(self, message, status_code=None, payload=None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


def to_halalas(amount):
    """Decimal SAR -> integer halalas (Moyasar's smallest-unit format)."""
    return int(Decimal(amount) * 100)


def from_halalas(amount):
    """Integer halalas -> Decimal SAR."""
    return Decimal(amount) / Decimal(100)


class MoyasarClient:
    """Thin, typed wrapper over the Moyasar REST API.

    ``transport`` is injectable so tests can use ``httpx.MockTransport``
    without patching.
    """

    def __init__(self, secret_key=None, base_url=None, transport=None, timeout=10.0):
        self._client = httpx.Client(
            base_url=(base_url or settings.MOYASAR_API_BASE_URL).rstrip("/"),
            auth=(secret_key or settings.MOYASAR_SECRET_KEY, ""),
            timeout=timeout,
            transport=transport,
        )

    def _request(self, method, path, json=None):
        try:
            response = self._client.request(method, path, json=json)
        except httpx.HTTPError as exc:
            raise MoyasarError(f"Moyasar request failed: {exc}") from exc
        if response.is_success:
            return response.json()
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        raise MoyasarError(
            payload.get("message", f"Moyasar returned HTTP {response.status_code}"),
            status_code=response.status_code,
            payload=payload,
        )

    def fetch_payment(self, payment_id):
        return self._request("GET", f"/payments/{payment_id}")

    def refund_payment(self, payment_id, amount_halalas=None):
        body = {"amount": amount_halalas} if amount_halalas is not None else None
        return self._request("POST", f"/payments/{payment_id}/refund", json=body)

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()


class ZatcaError(Exception):
    """A failed Fatoora call. ``retryable`` separates transport faults and
    throttling/5xx from definitive document rejections (4xx validation)."""

    def __init__(self, message, status_code=None, payload=None, retryable=False):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}
        self.retryable = retryable


class ZatcaClient:
    """Thin wrapper over the ZATCA Fatoora portal API.

    ``transport`` is injectable so tests can use ``httpx.MockTransport``
    without patching. ``csid``/``secret`` are the Basic auth pair — the
    compliance CSID during onboarding, the production CSID afterwards.
    """

    def __init__(
        self, csid=None, secret=None, base_url=None, transport=None, timeout=30.0
    ):
        auth = (csid, secret) if csid is not None else None
        self._client = httpx.Client(
            base_url=(base_url or settings.ZATCA_API_BASE_URL).rstrip("/"),
            auth=auth,
            headers={"Accept-Version": "V2", "Accept-Language": "en"},
            timeout=timeout,
            transport=transport,
        )

    def _request(self, method, path, json=None, headers=None):
        try:
            response = self._client.request(method, path, json=json, headers=headers)
        except httpx.HTTPError as exc:
            raise ZatcaError(f"ZATCA request failed: {exc}", retryable=True) from exc
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        # 200 = accepted, 202 = accepted with warnings: both are stored.
        if response.is_success:
            payload["_http_status"] = response.status_code
            return payload
        raise ZatcaError(
            self._error_message(payload, response.status_code),
            status_code=response.status_code,
            payload=payload,
            retryable=response.status_code >= 500 or response.status_code == 429,
        )

    @staticmethod
    def _error_message(payload, status_code):
        errors = (payload.get("validationResults") or {}).get("errorMessages") or []
        if errors:
            return "; ".join(error.get("message", "") for error in errors)
        return payload.get("message", f"ZATCA returned HTTP {status_code}")

    def request_compliance_csid(self, csr_b64, otp):
        """Exchange a CSR + portal OTP for the compliance CSID."""
        return self._request(
            "POST", "/compliance", json={"csr": csr_b64}, headers={"OTP": otp}
        )

    def check_invoice_compliance(self, invoice_hash, invoice_uuid, invoice_b64):
        """Compliance-check a sample document against the compliance CSID."""
        return self._request(
            "POST",
            "/compliance/invoices",
            json={
                "invoiceHash": invoice_hash,
                "uuid": invoice_uuid,
                "invoice": invoice_b64,
            },
        )

    def request_production_csid(self, compliance_request_id):
        return self._request(
            "POST",
            "/production/csids",
            json={"compliance_request_id": compliance_request_id},
        )

    def report_invoice(self, invoice_hash, invoice_uuid, invoice_b64):
        """Report a signed simplified invoice (Clearance-Status: 0)."""
        return self._request(
            "POST",
            "/invoices/reporting/single",
            json={
                "invoiceHash": invoice_hash,
                "uuid": invoice_uuid,
                "invoice": invoice_b64,
            },
            headers={"Clearance-Status": "0"},
        )

    def clear_invoice(self, invoice_hash, invoice_uuid, invoice_b64):
        """Submit a standard invoice for clearance (ZATCA stamps it)."""
        return self._request(
            "POST",
            "/invoices/clearance/single",
            json={
                "invoiceHash": invoice_hash,
                "uuid": invoice_uuid,
                "invoice": invoice_b64,
            },
            headers={"Clearance-Status": "1"},
        )

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()
