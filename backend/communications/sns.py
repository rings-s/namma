"""Amazon SNS message signature verification.

Every envelope hitting the SES webhook is authenticated against the
signature AWS embeds in it (per the SNS developer guide's "verifying
message signatures"): the signing certificate is fetched from an
``sns.<region>.amazonaws.com`` HTTPS URL only, cached, and used to check
the RSA signature over the canonical string for the message type. Nothing
unverified is ever stored or acted on.
"""

import base64
import re
from urllib.parse import urlsplit

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509 import load_pem_x509_certificate
from cryptography.x509.oid import NameOID
from django.conf import settings
from django.core.cache import cache

#: Exact-host match, never substring — blocks sns.x.amazonaws.com.evil.com.
_SIGNING_CERT_HOST = re.compile(r"^sns\.[a-z0-9-]+\.amazonaws\.com$")

#: Fields signed per message type, in AWS's documented canonical order.
_SIGNED_FIELDS = {
    "Notification": (
        "Message",
        "MessageId",
        "Subject",
        "Timestamp",
        "TopicArn",
        "Type",
    ),
    "SubscriptionConfirmation": (
        "Message",
        "MessageId",
        "SubscribeURL",
        "Timestamp",
        "Token",
        "TopicArn",
        "Type",
    ),
    "UnsubscribeConfirmation": (
        "Message",
        "MessageId",
        "SubscribeURL",
        "Timestamp",
        "Token",
        "TopicArn",
        "Type",
    ),
}

#: SignatureVersion → digest: "1" is SHA1withRSA, "2" is SHA256withRSA.
_DIGESTS = {"1": hashes.SHA1, "2": hashes.SHA256}

_CERT_CACHE_PREFIX = "sns-signing-cert:"
_CERT_CACHE_SECONDS = 60 * 60 * 24


class SNSVerificationError(Exception):
    """The SNS envelope failed authenticity checks."""


def _signing_certificate(cert_url):
    parts = urlsplit(cert_url)
    hostname = parts.hostname or ""
    if (
        parts.scheme != "https"
        or not _SIGNING_CERT_HOST.match(hostname)
        or not parts.path.endswith(".pem")
    ):
        raise SNSVerificationError(f"Refusing SNS SigningCertURL: {cert_url!r}")
    cache_key = f"{_CERT_CACHE_PREFIX}{cert_url}"
    pem = cache.get(cache_key)
    if pem is None:
        try:
            response = httpx.get(cert_url, timeout=10.0)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SNSVerificationError(
                f"Could not fetch the SNS signing certificate: {exc}"
            ) from exc
        pem = response.content
        cache.set(cache_key, pem, _CERT_CACHE_SECONDS)
    try:
        certificate = load_pem_x509_certificate(pem)
    except ValueError as exc:
        raise SNSVerificationError("SNS signing certificate is not valid PEM.") from exc
    common_names = certificate.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    if not any(attr.value == "sns.amazonaws.com" for attr in common_names):
        raise SNSVerificationError(
            "SNS signing certificate subject is not sns.amazonaws.com."
        )
    return certificate


def verify_sns_message(envelope):
    """Raise ``SNSVerificationError`` unless ``envelope`` was signed by SNS
    *and* belongs to our pinned topic.

    The signature only proves AWS SNS signed the message — an attacker's
    own topic produces validly signed envelopes too, so the TopicArn must
    match the configured topic exactly. Fails closed when unconfigured.
    """
    expected_topic = settings.AWS_SES_SNS_TOPIC_ARN
    if not expected_topic or envelope.get("TopicArn") != expected_topic:
        raise SNSVerificationError("SNS TopicArn is not trusted.")
    fields = _SIGNED_FIELDS.get(envelope.get("Type"))
    if fields is None:
        raise SNSVerificationError(
            f"Unsupported SNS message type: {envelope.get('Type')!r}"
        )
    digest = _DIGESTS.get(str(envelope.get("SignatureVersion", "1")))
    if digest is None:
        raise SNSVerificationError("Unsupported SNS SignatureVersion.")
    try:
        signature = base64.b64decode(envelope["Signature"], validate=True)
    except (KeyError, TypeError, ValueError) as exc:
        raise SNSVerificationError("Missing or unreadable SNS Signature.") from exc
    # Optional fields (e.g. Subject) are only signed when present.
    canonical = "".join(
        f"{field}\n{envelope[field]}\n" for field in fields if field in envelope
    ).encode()
    certificate = _signing_certificate(str(envelope.get("SigningCertURL", "")))
    try:
        certificate.public_key().verify(
            signature, canonical, padding.PKCS1v15(), digest()
        )
    except InvalidSignature as exc:
        raise SNSVerificationError("SNS signature does not match.") from exc
