"""Outbound messaging gateway clients: Taqnyat (SMS) and Amazon SES (email).

Taqnyat — official API contract (github.com/taqnyat/OpenAPI, api.taqnyat.sa):
- Server ``https://api.taqnyat.sa``; ``Authorization: Bearer <token>``.
- ``POST /v1/messages`` body: ``recipients`` (international format, no ``00``
  or ``+``), ``body``, ``sender`` (predefined sender name), optional
  ``scheduledDatetime`` (``YYYY-MM-DDTHH:MM``).
- 201 response: ``statusCode, messageId, cost (SAR string), currency,
  totalCount, msgLength, accepted, rejected``.
- ``GET /account/balance`` for the account balance.

Amazon SES — SES v2 ``SendEmail`` with ``Simple`` content. Sends carry the
account configuration set so bounces/complaints/deliveries flow back through
SNS to our webhook, plus per-message tags for reconciliation.
"""

import hashlib
import hmac

import boto3
import httpx
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings


class TaqnyatError(Exception):
    """A non-2xx response from the Taqnyat API."""

    def __init__(self, message, status_code=None, payload=None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


def normalize_msisdn(number):
    """Strip ``+``, ``00`` and separators: Taqnyat wants ``9665XXXXXXXX``."""
    digits = "".join(ch for ch in str(number) if ch.isdigit())
    if digits.startswith("00"):
        digits = digits[2:]
    return digits


class TaqnyatClient:
    """Thin wrapper over the Taqnyat REST API.

    ``transport`` is injectable so tests can use ``httpx.MockTransport``
    without patching.
    """

    def __init__(self, bearer_token=None, base_url=None, transport=None, timeout=10.0):
        token = bearer_token or settings.TAQNYAT_BEARER_TOKEN
        self._client = httpx.Client(
            base_url=(base_url or settings.TAQNYAT_API_BASE_URL).rstrip("/"),
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
            transport=transport,
        )

    def _request(self, method, path, json=None):
        try:
            response = self._client.request(method, path, json=json)
        except httpx.HTTPError as exc:
            raise TaqnyatError(f"Taqnyat request failed: {exc}") from exc
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        if response.is_success:
            return payload
        raise TaqnyatError(
            payload.get("message", f"Taqnyat returned HTTP {response.status_code}"),
            status_code=response.status_code,
            payload=payload,
        )

    def send_sms(self, recipients, body, sender=None, scheduled_at=None):
        payload = {
            "recipients": [normalize_msisdn(number) for number in recipients],
            "body": body,
            "sender": sender or settings.TAQNYAT_SMS_SENDER,
        }
        if scheduled_at is not None:
            payload["scheduledDatetime"] = scheduled_at.strftime("%Y-%m-%dT%H:%M")
        return self._request("POST", "/v1/messages", json=payload)

    def get_balance(self):
        return self._request("GET", "/account/balance")

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()


class SESError(Exception):
    """A failed SES send. ``retryable`` separates transport/throttling
    problems (worth retrying) from definitive rejections (final)."""

    def __init__(self, message, code=None, retryable=False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


#: SES error codes that mean "try again later", not "this send is bad".
SES_RETRYABLE_CODES = frozenset(
    {"TooManyRequestsException", "LimitExceededException", "InternalServiceError"}
)


class SESEmailClient:
    """Thin wrapper over the SES v2 ``SendEmail`` API.

    ``client`` is injectable so tests can pass a stub instead of patching
    boto3 (same spirit as the Taqnyat ``transport`` hook).
    """

    def __init__(self, client=None):
        self._client = client or boto3.client(
            "sesv2",
            region_name=settings.AWS_SES_REGION,
            # Blank settings fall through to boto3's default chain (env,
            # shared config, instance role) instead of failing outright.
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
        )

    def send_email(
        self,
        to_addresses,
        subject,
        html_body=None,
        text_body=None,
        from_email=None,
        tags=None,
    ):
        """Send one email; returns the SES message id."""
        body = {}
        if html_body:
            body["Html"] = {"Data": html_body, "Charset": "UTF-8"}
        if text_body:
            body["Text"] = {"Data": text_body, "Charset": "UTF-8"}
        if not body:
            raise SESError("An email needs an HTML or text body.")
        params = {
            "FromEmailAddress": from_email or settings.SES_FROM_EMAIL,
            "Destination": {"ToAddresses": list(to_addresses)},
            "Content": {
                "Simple": {
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": body,
                }
            },
        }
        if settings.AWS_SES_CONFIGURATION_SET:
            params["ConfigurationSetName"] = settings.AWS_SES_CONFIGURATION_SET
        if tags:
            params["EmailTags"] = [
                {"Name": name, "Value": value} for name, value in tags.items()
            ]
        try:
            response = self._client.send_email(**params)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            raise SESError(
                exc.response.get("Error", {}).get("Message", str(exc)),
                code=code,
                retryable=code in SES_RETRYABLE_CODES,
            ) from exc
        except BotoCoreError as exc:
            # Connection/endpoint problems: nothing was rejected, retry.
            raise SESError(f"SES request failed: {exc}", retryable=True) from exc
        return str(response.get("MessageId", ""))


class WhatsAppError(Exception):
    """A failed WhatsApp Cloud API call. ``retryable`` separates transient
    failures (network, HTTP 429/5xx) worth retrying from definitive rejections
    (invalid number, expired token, template not approved) that are final."""

    def __init__(self, message, status_code=None, payload=None, retryable=False):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}
        self.retryable = retryable


class WhatsAppCloudClient:
    """Thin wrapper over the Meta WhatsApp Cloud API (Graph API).

    Sends go to ``POST /{version}/{phone_number_id}/messages`` with a Bearer
    access token. ``transport`` is injectable so tests run against
    ``httpx.MockTransport`` without network, mirroring the Taqnyat client.
    """

    def __init__(
        self,
        access_token=None,
        phone_number_id=None,
        base_url=None,
        api_version=None,
        transport=None,
        timeout=10.0,
    ):
        self.phone_number_id = phone_number_id or settings.WHATSAPP_PHONE_NUMBER_ID
        token = (
            access_token if access_token is not None else settings.WHATSAPP_ACCESS_TOKEN
        )
        version = api_version or settings.WHATSAPP_API_VERSION
        base = (base_url or settings.WHATSAPP_API_BASE_URL).rstrip("/")
        self._client = httpx.Client(
            base_url=f"{base}/{version}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
            transport=transport,
        )

    def _post_message(self, payload):
        path = f"/{self.phone_number_id}/messages"
        try:
            response = self._client.post(path, json=payload)
        except httpx.HTTPError as exc:
            raise WhatsAppError(
                f"WhatsApp request failed: {exc}", retryable=True
            ) from exc
        try:
            data = response.json()
        except ValueError:
            data = {}
        if response.is_success:
            return data
        error = data.get("error") if isinstance(data.get("error"), dict) else {}
        raise WhatsAppError(
            error.get("message") or f"WhatsApp returned HTTP {response.status_code}",
            status_code=response.status_code,
            payload=data,
            # 429 + 5xx are transient; 4xx (bad number/token/template) are final.
            retryable=response.status_code == 429 or response.status_code >= 500,
        )

    def send_text(self, to, body, preview_url=False):
        """Free-form text — only deliverable inside the 24h customer service
        window. Use ``send_template`` to (re)open a conversation."""
        return self._post_message(
            {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": normalize_msisdn(to),
                "type": "text",
                "text": {"preview_url": preview_url, "body": body},
            }
        )

    def send_template(self, to, template_name, language_code, components=None):
        """Pre-approved template message — the only kind that can initiate a
        conversation (reminders, marketing, OTP). ``components`` carries the
        body/header/button variables per the Cloud API schema."""
        template = {"name": template_name, "language": {"code": language_code}}
        if components:
            template["components"] = components
        return self._post_message(
            {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": normalize_msisdn(to),
                "type": "template",
                "template": template,
            }
        )

    @staticmethod
    def first_message_id(response):
        """The ``wamid.*`` id of the first message in a send response."""
        messages = response.get("messages") or []
        return str(messages[0].get("id", "")) if messages else ""

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()


def verify_whatsapp_signature(payload_body, signature_header, app_secret=None):
    """True iff ``payload_body`` (raw request bytes) carries a valid Meta
    ``X-Hub-Signature-256`` HMAC. Fails closed when the app secret is unset, so
    a misconfigured deployment rejects webhooks rather than trusting them."""
    secret = app_secret if app_secret is not None else settings.WHATSAPP_APP_SECRET
    if not secret or not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(
        secret.encode("utf-8"), payload_body, hashlib.sha256
    ).hexdigest()
    provided = signature_header.split("=", 1)[1]
    return hmac.compare_digest(expected, provided)
