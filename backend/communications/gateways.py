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
