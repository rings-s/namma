"""ZATCA Phase-2 (Fatoora) e-invoicing engine: keys, CSRs, UBL 2.1 XML,
invoice hashing, XAdES stamping and QR TLV codes.

Implements the ZATCA e-invoicing security specification:
- Device keys are ECDSA on secp256k1; CSRs carry the certificate-template
  extension (sandbox/simulation/production) and a dirName SAN with the
  serial, VAT number, invoice-type title, address and business category.
- The invoice hash is SHA-256 over the C14N11-canonicalized XML after
  removing UBLExtensions, the cac:Signature block and the QR document
  reference; each invoice carries the previous one's hash (PIH) and a
  per-device counter (ICV).
- Simplified invoices are stamped by the device (XAdES B-B inside
  UBLExtensions) and *reported*; standard invoices are submitted unsigned
  for *clearance*, where ZATCA itself applies the stamp.
- The QR code is a base64 TLV (tags 1-9) embedded in the XML and rendered
  by clients.

Key material at rest is encrypted with Fernet (settings.ZATCA_KEY_ENCRYPTION_KEY).
"""

import base64
import hashlib
import struct
from decimal import ROUND_HALF_UP, Decimal

from cryptography import x509
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.name import _ASN1Type
from cryptography.x509.oid import NameOID, ObjectIdentifier
from django.conf import settings
from lxml import etree

#: PIH for the first invoice of a chain: base64 of the SHA-256 hex of "0".
INITIAL_PREVIOUS_INVOICE_HASH = base64.b64encode(
    hashlib.sha256(b"0").hexdigest().encode()
).decode()

#: Certificate template names per ZATCA environment (CSR extension
#: 1.3.6.1.4.1.311.20.2). Production certificates only sign production
#: invoices; sandbox/simulation names yield test CSIDs.
CERTIFICATE_TEMPLATES = {
    "sandbox": "TSTZATCA-Code-Signing",
    "simulation": "PREZATCA-Code-Signing",
    "production": "ZATCA-Code-Signing",
}

UBL_NSMAP = {
    None: "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
}
CAC = UBL_NSMAP["cac"]
CBC = UBL_NSMAP["cbc"]
EXT = UBL_NSMAP["ext"]


class ZatcaCryptoError(Exception):
    """Key material is missing, corrupt or not decryptable."""


# ---------------------------------------------------------------------------
# Key material & encryption at rest
# ---------------------------------------------------------------------------


def _fernet():
    key = settings.ZATCA_KEY_ENCRYPTION_KEY
    if not key:
        raise ZatcaCryptoError(
            "ZATCA_KEY_ENCRYPTION_KEY is not configured; refusing to handle "
            "ZATCA key material without encryption at rest."
        )
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as exc:
        raise ZatcaCryptoError(
            "ZATCA_KEY_ENCRYPTION_KEY is not a valid Fernet key."
        ) from exc


def encrypt_secret(plaintext):
    """Encrypt a secret (PEM key, CSID secret) for storage."""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext):
    """Decrypt a stored secret. Raises ZatcaCryptoError on tampering."""
    from cryptography.fernet import InvalidToken

    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise ZatcaCryptoError("Stored ZATCA secret failed decryption.") from exc


def generate_private_key():
    """New device signing key — ZATCA mandates ECDSA over secp256k1."""
    return ec.generate_private_key(ec.SECP256K1())


def private_key_to_pem(private_key):
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


def private_key_from_pem(pem):
    return serialization.load_pem_private_key(pem.encode(), password=None)


# ---------------------------------------------------------------------------
# CSR generation
# ---------------------------------------------------------------------------

#: dirName SAN attribute OIDs from the ZATCA CSR specification.
_OID_UID = ObjectIdentifier("0.9.2342.19200300.100.1.1")
_OID_TITLE = NameOID.TITLE
_OID_REGISTERED_ADDRESS = ObjectIdentifier("2.5.4.26")
_OID_BUSINESS_CATEGORY = NameOID.BUSINESS_CATEGORY
_OID_CERT_TEMPLATE = ObjectIdentifier("1.3.6.1.4.1.311.20.2")


def _der_utf8_string(value):
    """Minimal DER encoding of an ASN.1 UTF8String (template name is short)."""
    encoded = value.encode()
    if len(encoded) > 127:
        raise ZatcaCryptoError("Certificate template name too long for short-form DER.")
    return b"\x0c" + bytes([len(encoded)]) + encoded


def generate_csr(private_key, device, environment=None):
    """Build the ZATCA-spec CSR for a device.

    The serial number must be unique per device and stable across renewals:
    ``1-<solution>|2-<model>|3-<device uuid>``.
    """
    organization = device.organization
    environment = environment or settings.ZATCA_ENVIRONMENT
    template = CERTIFICATE_TEMPLATES.get(environment)
    if template is None:
        raise ZatcaCryptoError(f"Unknown ZATCA environment {environment!r}.")
    if not organization.vat_number:
        raise ZatcaCryptoError(
            "The organization has no VAT number; set it before onboarding."
        )

    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "SA"),
            x509.NameAttribute(
                NameOID.ORGANIZATIONAL_UNIT_NAME,
                device.branch.name if device.branch_id else organization.name,
            ),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization.name),
            x509.NameAttribute(NameOID.COMMON_NAME, device.device_name),
        ]
    )
    san_directory = x509.Name(
        [
            # UTF8String: the ZATCA serial contains "|", which the default
            # PrintableString encoding for serialNumber does not allow.
            x509.NameAttribute(
                NameOID.SERIAL_NUMBER,
                f"1-Namaa|2-1.0|3-{device.pk}",
                _type=_ASN1Type.UTF8String,
            ),
            x509.NameAttribute(_OID_UID, organization.vat_number),
            # "1100": the device issues standard and simplified documents.
            x509.NameAttribute(_OID_TITLE, "1100"),
            x509.NameAttribute(
                _OID_REGISTERED_ADDRESS,
                f"{organization.building_number} {organization.street_name}, "
                f"{organization.district}, {organization.city}".strip(" ,"),
            ),
            x509.NameAttribute(
                _OID_BUSINESS_CATEGORY, organization.industry or "Services"
            ),
        ]
    )
    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(subject)
        .add_extension(
            x509.UnrecognizedExtension(_OID_CERT_TEMPLATE, _der_utf8_string(template)),
            critical=False,
        )
        .add_extension(
            x509.SubjectAlternativeName([x509.DirectoryName(san_directory)]),
            critical=False,
        )
        .sign(private_key, hashes.SHA256())
    )
    return csr.public_bytes(serialization.Encoding.PEM).decode()


def csr_to_base64(csr_pem):
    """Fatoora expects the whole PEM (headers included) base64-wrapped."""
    return base64.b64encode(csr_pem.encode()).decode()


# ---------------------------------------------------------------------------
# Amount formatting
# ---------------------------------------------------------------------------


def _money(value):
    """Format a decimal amount the way ZATCA validates it: 2dp, half-up."""
    return str(Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


# ---------------------------------------------------------------------------
# UBL 2.1 invoice XML
# ---------------------------------------------------------------------------


def _sub(parent, namespace, tag, text=None, **attrs):
    element = etree.SubElement(parent, f"{{{namespace}}}{tag}")
    if text is not None:
        element.text = text
    for name, value in attrs.items():
        element.set(name, value)
    return element


def _document_reference(root, doc_id, **payload):
    ref = _sub(root, CAC, "AdditionalDocumentReference")
    _sub(ref, CBC, "ID", doc_id)
    if "uuid" in payload:
        _sub(ref, CBC, "UUID", payload["uuid"])
    if "embedded" in payload:
        attachment = _sub(ref, CAC, "Attachment")
        _sub(
            attachment,
            CBC,
            "EmbeddedDocumentBinaryObject",
            payload["embedded"],
            mimeCode="text/plain",
        )
    return ref


def _supplier_party(root, organization):
    supplier = _sub(root, CAC, "AccountingSupplierParty")
    party = _sub(supplier, CAC, "Party")
    if organization.commercial_registration_number:
        identification = _sub(party, CAC, "PartyIdentification")
        _sub(
            identification,
            CBC,
            "ID",
            organization.commercial_registration_number,
            schemeID="CRN",
        )
    address = _sub(party, CAC, "PostalAddress")
    _sub(address, CBC, "StreetName", organization.street_name or "-")
    _sub(address, CBC, "BuildingNumber", organization.building_number or "0000")
    _sub(address, CBC, "CitySubdivisionName", organization.district or "-")
    _sub(address, CBC, "CityName", organization.city or "-")
    _sub(address, CBC, "PostalZone", organization.postal_code or "00000")
    country = _sub(address, CAC, "Country")
    _sub(country, CBC, "IdentificationCode", "SA")
    tax_scheme_party = _sub(party, CAC, "PartyTaxScheme")
    _sub(tax_scheme_party, CBC, "CompanyID", organization.vat_number)
    _sub(_sub(tax_scheme_party, CAC, "TaxScheme"), CBC, "ID", "VAT")
    legal = _sub(party, CAC, "PartyLegalEntity")
    _sub(legal, CBC, "RegistrationName", organization.name)


def _customer_party(root, customer):
    """Buyer block. Simplified invoices allow an anonymous consumer."""
    buyer = _sub(root, CAC, "AccountingCustomerParty")
    party = _sub(buyer, CAC, "Party")
    if customer is not None:
        legal = _sub(party, CAC, "PartyLegalEntity")
        name = f"{customer.first_name} {customer.last_name}".strip()
        _sub(legal, CBC, "RegistrationName", name or "Consumer")


def _tax_totals(root, e_invoice, taxable_amount, tax_amount):
    # First TaxTotal: the document VAT amount alone (mandatory KSA rule).
    first = _sub(root, CAC, "TaxTotal")
    _sub(first, CBC, "TaxAmount", _money(tax_amount), currencyID="SAR")
    # Second TaxTotal: the per-category breakdown.
    second = _sub(root, CAC, "TaxTotal")
    _sub(second, CBC, "TaxAmount", _money(tax_amount), currencyID="SAR")
    subtotal = _sub(second, CAC, "TaxSubtotal")
    _sub(subtotal, CBC, "TaxableAmount", _money(taxable_amount), currencyID="SAR")
    _sub(subtotal, CBC, "TaxAmount", _money(tax_amount), currencyID="SAR")
    category = _sub(subtotal, CAC, "TaxCategory")
    _sub(category, CBC, "ID", "S")
    _sub(category, CBC, "Percent", "15.00")
    _sub(_sub(category, CAC, "TaxScheme"), CBC, "ID", "VAT")


def _monetary_total(root, invoice):
    taxable = invoice.subtotal - invoice.discount_amount
    total = _sub(root, CAC, "LegalMonetaryTotal")
    _sub(total, CBC, "LineExtensionAmount", _money(invoice.subtotal), currencyID="SAR")
    _sub(total, CBC, "TaxExclusiveAmount", _money(taxable), currencyID="SAR")
    _sub(
        total, CBC, "TaxInclusiveAmount", _money(invoice.total_amount), currencyID="SAR"
    )
    _sub(
        total,
        CBC,
        "AllowanceTotalAmount",
        _money(invoice.discount_amount),
        currencyID="SAR",
    )
    _sub(total, CBC, "PrepaidAmount", "0.00", currencyID="SAR")
    _sub(total, CBC, "PayableAmount", _money(invoice.total_amount), currencyID="SAR")


def _invoice_lines(root, invoice):
    """One UBL line per sale item; invoices without a sale get one
    aggregate line so manually issued invoices remain reportable."""
    sale = invoice.sale
    items = list(sale.items.all()) if sale is not None else []
    if not items:
        _invoice_line(
            root,
            line_id="1",
            name=f"Invoice {invoice.invoice_number}",
            quantity=Decimal(1),
            line_total=invoice.subtotal,
            tax_amount=invoice.tax_amount,
        )
        return
    # Distribute header VAT across lines proportionally to keep line tax
    # totals consistent with the document total despite per-line rounding.
    subtotal = sum((item.total_price for item in items), Decimal(0))
    remaining_tax = Decimal(invoice.tax_amount)
    for index, item in enumerate(items, start=1):
        if index == len(items) or subtotal == 0:
            line_tax = remaining_tax
        else:
            share = (Decimal(item.total_price) / subtotal) * Decimal(invoice.tax_amount)
            line_tax = share.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        remaining_tax -= line_tax
        _invoice_line(
            root,
            line_id=str(index),
            name=item.description
            or (item.service.name if item.service_id else None)
            or (item.product.name if item.product_id else None)
            or f"Item {index}",
            quantity=Decimal(item.quantity),
            line_total=item.total_price,
            tax_amount=line_tax,
        )


def _invoice_line(root, line_id, name, quantity, line_total, tax_amount):
    line = _sub(root, CAC, "InvoiceLine")
    _sub(line, CBC, "ID", line_id)
    _sub(line, CBC, "InvoicedQuantity", str(quantity), unitCode="PCE")
    _sub(line, CBC, "LineExtensionAmount", _money(line_total), currencyID="SAR")
    line_tax = _sub(line, CAC, "TaxTotal")
    _sub(line_tax, CBC, "TaxAmount", _money(tax_amount), currencyID="SAR")
    _sub(
        line_tax,
        CBC,
        "RoundingAmount",
        _money(Decimal(line_total) + Decimal(tax_amount)),
        currencyID="SAR",
    )
    item = _sub(line, CAC, "Item")
    _sub(item, CBC, "Name", name)
    category = _sub(item, CAC, "ClassifiedTaxCategory")
    _sub(category, CBC, "ID", "S")
    _sub(category, CBC, "Percent", "15.00")
    _sub(_sub(category, CAC, "TaxScheme"), CBC, "ID", "VAT")
    price = _sub(line, CAC, "Price")
    unit_price = Decimal(line_total) / quantity if quantity else Decimal(line_total)
    _sub(price, CBC, "PriceAmount", _money(unit_price), currencyID="SAR")


def build_invoice_xml(e_invoice):
    """Unsigned UBL 2.1 document for an EInvoice row (no QR, no stamp)."""
    from financials.models import EInvoice

    invoice = e_invoice.invoice
    organization = e_invoice.organization
    issued_at = invoice.issued_at or invoice.created_at

    root = etree.Element(f"{{{UBL_NSMAP[None]}}}Invoice", nsmap=UBL_NSMAP)
    _sub(root, CBC, "ProfileID", "reporting:1.0")
    _sub(root, CBC, "ID", invoice.invoice_number)
    _sub(root, CBC, "UUID", e_invoice.uuid)
    _sub(root, CBC, "IssueDate", issued_at.date().isoformat())
    _sub(root, CBC, "IssueTime", issued_at.time().replace(microsecond=0).isoformat())
    subtype = (
        "0200000"
        if e_invoice.invoice_type == EInvoice.InvoiceType.SIMPLIFIED
        else "0100000"
    )
    _sub(root, CBC, "InvoiceTypeCode", "388", name=subtype)
    _sub(root, CBC, "DocumentCurrencyCode", "SAR")
    _sub(root, CBC, "TaxCurrencyCode", "SAR")
    _document_reference(root, "ICV", uuid=str(e_invoice.icv))
    _document_reference(root, "PIH", embedded=e_invoice.previous_invoice_hash)
    _supplier_party(root, organization)
    _customer_party(root, invoice.customer)
    _tax_totals(
        root,
        e_invoice,
        taxable_amount=invoice.subtotal - invoice.discount_amount,
        tax_amount=invoice.tax_amount,
    )
    _monetary_total(root, invoice)
    _invoice_lines(root, invoice)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8").decode()


def _note_amounts(gross):
    """Split a VAT-inclusive note total into (net, tax) at the KSA 15% rate.

    Credit/Debit notes store a single gross ``amount`` (VAT-inclusive, same
    semantics as ``Invoice.total_amount``); ZATCA needs the net line-extension
    amount and the VAT separately.
    """
    gross = Decimal(gross)
    net = (gross / Decimal("1.15")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return net, gross - net


def build_credit_debit_note_xml(e_invoice):
    """Unsigned UBL 2.1 document for a credit (381) or debit (383) note.

    ZATCA carries credit/debit notes on the *Invoice* schema, distinguished by
    InvoiceTypeCode, and requires a ``cac:BillingReference`` to the original
    invoice plus a reason for issuance (``cac:PaymentMeans/cbc:InstructionNote``).
    """
    from financials.models import EInvoice

    note = e_invoice.credit_note or e_invoice.debit_note
    if note is None:
        raise ZatcaCryptoError("Note e-invoice has no credit_note/debit_note set.")
    original_invoice = e_invoice.invoice
    organization = e_invoice.organization
    issued_at = note.issued_at or note.created_at
    type_code = EInvoice.ZATCA_TYPE_CODE[e_invoice.document_type]
    number = getattr(note, "credit_note_number", None) or note.debit_note_number
    net, tax = _note_amounts(note.amount)

    # The original invoice's reported UUID anchors the note to the ZATCA chain.
    original_e_invoice = (
        original_invoice.e_invoices.filter(document_type=EInvoice.DocumentType.INVOICE)
        .exclude(status__in=(EInvoice.Status.REJECTED, EInvoice.Status.FAILED))
        .order_by("created_at")
        .first()
    )

    root = etree.Element(f"{{{UBL_NSMAP[None]}}}Invoice", nsmap=UBL_NSMAP)
    _sub(root, CBC, "ProfileID", "reporting:1.0")
    _sub(root, CBC, "ID", number)
    _sub(root, CBC, "UUID", e_invoice.uuid)
    _sub(root, CBC, "IssueDate", issued_at.date().isoformat())
    _sub(root, CBC, "IssueTime", issued_at.time().replace(microsecond=0).isoformat())
    subtype = (
        "0200000"
        if e_invoice.invoice_type == EInvoice.InvoiceType.SIMPLIFIED
        else "0100000"
    )
    _sub(root, CBC, "InvoiceTypeCode", type_code, name=subtype)
    _sub(root, CBC, "DocumentCurrencyCode", "SAR")
    _sub(root, CBC, "TaxCurrencyCode", "SAR")
    # BillingReference: the invoice this note adjusts (mandatory for 381/383).
    billing = _sub(root, CAC, "BillingReference")
    doc_ref = _sub(billing, CAC, "InvoiceDocumentReference")
    _sub(doc_ref, CBC, "ID", original_invoice.invoice_number)
    if original_e_invoice is not None:
        _sub(doc_ref, CBC, "UUID", original_e_invoice.uuid)
    _document_reference(root, "ICV", uuid=str(e_invoice.icv))
    _document_reference(root, "PIH", embedded=e_invoice.previous_invoice_hash)
    _supplier_party(root, organization)
    _customer_party(root, original_invoice.customer)
    # Reason for issuance — ZATCA mandates it on notes.
    payment_means = _sub(root, CAC, "PaymentMeans")
    _sub(payment_means, CBC, "PaymentMeansCode", "10")
    _sub(
        payment_means,
        CBC,
        "InstructionNote",
        note.reason_text or note.reason_code or "Adjustment",
    )
    _tax_totals(root, e_invoice, taxable_amount=net, tax_amount=tax)
    total = _sub(root, CAC, "LegalMonetaryTotal")
    _sub(total, CBC, "LineExtensionAmount", _money(net), currencyID="SAR")
    _sub(total, CBC, "TaxExclusiveAmount", _money(net), currencyID="SAR")
    _sub(total, CBC, "TaxInclusiveAmount", _money(note.amount), currencyID="SAR")
    _sub(total, CBC, "PrepaidAmount", "0.00", currencyID="SAR")
    _sub(total, CBC, "PayableAmount", _money(note.amount), currencyID="SAR")
    _invoice_line(
        root,
        line_id="1",
        name=note.reason_text or f"Adjustment for {original_invoice.invoice_number}",
        quantity=Decimal(1),
        line_total=net,
        tax_amount=tax,
    )
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8").decode()


# ---------------------------------------------------------------------------
# Invoice hashing (ZATCA canonical transform)
# ---------------------------------------------------------------------------

_HASH_EXCLUDED_XPATHS = (
    "//ext:UBLExtensions",
    "//cac:Signature",
    "//cac:AdditionalDocumentReference[cbc:ID='QR']",
)
_XPATH_NS = {"ext": EXT, "cac": CAC, "cbc": CBC}


def compute_invoice_hash(xml_string):
    """base64(SHA-256) of the canonicalized invoice, per the ZATCA spec:
    strip UBLExtensions, the signature block and the QR reference, then
    canonicalize with C14N 1.1."""
    parser = etree.XMLParser(remove_blank_text=False, resolve_entities=False)
    root = etree.fromstring(xml_string.encode(), parser=parser)
    for xpath in _HASH_EXCLUDED_XPATHS:
        for node in root.xpath(xpath, namespaces=_XPATH_NS):
            node.getparent().remove(node)
    # lxml implements C14N 1.0; for these documents (no xml:id/xml:base,
    # namespaces declared once at the root) the output is byte-identical to
    # the C14N 1.1 the ZATCA spec names.
    canonical = etree.tostring(
        root, method="c14n", exclusive=False, with_comments=False
    )
    return base64.b64encode(hashlib.sha256(canonical).digest()).decode()


# ---------------------------------------------------------------------------
# QR code (TLV, tags 1-9)
# ---------------------------------------------------------------------------


def _tlv(tag, value):
    if len(value) > 255:
        raise ZatcaCryptoError(f"QR TLV tag {tag} value exceeds 255 bytes.")
    return struct.pack("BB", tag, len(value)) + value


def build_qr_tlv(
    seller_name,
    vat_number,
    timestamp,
    total_with_vat,
    vat_amount,
    invoice_hash,
    signature_b64=None,
    public_key_der=None,
    certificate_signature=None,
):
    """Base64 TLV string for the e-invoice QR. Tags 7-9 (stamp data) apply
    to simplified invoices; standard invoices carry tags 1-6 until ZATCA
    returns the cleared document."""
    payload = (
        _tlv(1, seller_name.encode())
        + _tlv(2, vat_number.encode())
        + _tlv(3, timestamp.strftime("%Y-%m-%dT%H:%M:%SZ").encode())
        + _tlv(4, _money(total_with_vat).encode())
        + _tlv(5, _money(vat_amount).encode())
        + _tlv(6, invoice_hash.encode())
    )
    if signature_b64 is not None:
        payload += _tlv(7, signature_b64.encode())
    if public_key_der is not None:
        payload += _tlv(8, public_key_der)
    if certificate_signature is not None:
        payload += _tlv(9, certificate_signature)
    return base64.b64encode(payload).decode()


def decode_qr_tlv(encoded):
    """Inverse of build_qr_tlv, used by tests and support tooling."""
    raw = base64.b64decode(encoded)
    fields, offset = {}, 0
    while offset < len(raw):
        tag, length = raw[offset], raw[offset + 1]
        fields[tag] = raw[offset + 2 : offset + 2 + length]
        offset += 2 + length
    return fields


# ---------------------------------------------------------------------------
# XAdES stamp (simplified invoices)
# ---------------------------------------------------------------------------

_SIGNED_PROPERTIES_TEMPLATE = (
    '<xades:SignedProperties xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" Id="xadesSignedProperties">'
    "<xades:SignedSignatureProperties>"
    "<xades:SigningTime>{signing_time}</xades:SigningTime>"
    "<xades:SigningCertificate>"
    "<xades:Cert>"
    "<xades:CertDigest>"
    '<ds:DigestMethod xmlns:ds="http://www.w3.org/2000/09/xmldsig#" Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>'
    '<ds:DigestValue xmlns:ds="http://www.w3.org/2000/09/xmldsig#">{cert_digest}</ds:DigestValue>'
    "</xades:CertDigest>"
    "<xades:IssuerSerial>"
    '<ds:X509IssuerName xmlns:ds="http://www.w3.org/2000/09/xmldsig#">{issuer_name}</ds:X509IssuerName>'
    '<ds:X509SerialNumber xmlns:ds="http://www.w3.org/2000/09/xmldsig#">{serial_number}</ds:X509SerialNumber>'
    "</xades:IssuerSerial>"
    "</xades:Cert>"
    "</xades:SigningCertificate>"
    "</xades:SignedSignatureProperties>"
    "</xades:SignedProperties>"
)

_UBL_EXTENSIONS_TEMPLATE = (
    '<ext:UBLExtensions xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2">'
    "<ext:UBLExtension>"
    "<ext:ExtensionURI>urn:oasis:names:specification:ubl:dsig:enveloped:xades</ext:ExtensionURI>"
    "<ext:ExtensionContent>"
    '<sig:UBLDocumentSignatures xmlns:sig="urn:oasis:names:specification:ubl:schema:xsd:CommonSignatureComponents-2" '
    'xmlns:sac="urn:oasis:names:specification:ubl:schema:xsd:SignatureAggregateComponents-2" '
    'xmlns:sbc="urn:oasis:names:specification:ubl:schema:xsd:SignatureBasicComponents-2">'
    "<sac:SignatureInformation>"
    '<cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">urn:oasis:names:specification:ubl:signature:1</cbc:ID>'
    "<sbc:ReferencedSignatureID>urn:oasis:names:specification:ubl:signature:Invoice</sbc:ReferencedSignatureID>"
    '<ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#" Id="signature">'
    "<ds:SignedInfo>"
    '<ds:CanonicalizationMethod Algorithm="http://www.w3.org/2006/12/xml-c14n11"/>'
    '<ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#ecdsa-sha256"/>'
    '<ds:Reference Id="invoiceSignedData" URI="">'
    "<ds:Transforms>"
    '<ds:Transform Algorithm="http://www.w3.org/TR/1999/REC-xpath-19991116">'
    "<ds:XPath>not(//ancestor-or-self::ext:UBLExtensions)</ds:XPath>"
    "</ds:Transform>"
    '<ds:Transform Algorithm="http://www.w3.org/TR/1999/REC-xpath-19991116">'
    "<ds:XPath>not(//ancestor-or-self::cac:Signature)</ds:XPath>"
    "</ds:Transform>"
    '<ds:Transform Algorithm="http://www.w3.org/TR/1999/REC-xpath-19991116">'
    "<ds:XPath>not(//ancestor-or-self::cac:AdditionalDocumentReference[cbc:ID='QR'])</ds:XPath>"
    "</ds:Transform>"
    '<ds:Transform Algorithm="http://www.w3.org/2006/12/xml-c14n11"/>'
    "</ds:Transforms>"
    '<ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>'
    "<ds:DigestValue>{invoice_hash}</ds:DigestValue>"
    "</ds:Reference>"
    '<ds:Reference Type="http://www.w3.org/2000/09/xmldsig#SignatureProperties" URI="#xadesSignedProperties">'
    '<ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>'
    "<ds:DigestValue>{signed_properties_hash}</ds:DigestValue>"
    "</ds:Reference>"
    "</ds:SignedInfo>"
    "<ds:SignatureValue>{signature_value}</ds:SignatureValue>"
    "<ds:KeyInfo>"
    "<ds:X509Data>"
    "<ds:X509Certificate>{certificate}</ds:X509Certificate>"
    "</ds:X509Data>"
    "</ds:KeyInfo>"
    "<ds:Object>"
    '<xades:QualifyingProperties xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" Target="signature">'
    "{signed_properties}"
    "</xades:QualifyingProperties>"
    "</ds:Object>"
    "</ds:Signature>"
    "</sac:SignatureInformation>"
    "</sig:UBLDocumentSignatures>"
    "</ext:ExtensionContent>"
    "</ext:UBLExtension>"
    "</ext:UBLExtensions>"
)


def _certificate_digest(certificate_b64):
    """ZATCA hashes the base64 certificate string and base64-encodes the
    hex digest (matches the official SDK output)."""
    return base64.b64encode(
        hashlib.sha256(certificate_b64.encode()).hexdigest().encode()
    ).decode()


def _signed_properties(certificate_b64, signing_time):
    certificate = x509.load_der_x509_certificate(base64.b64decode(certificate_b64))
    issuer = certificate.issuer.rfc4514_string()
    return _SIGNED_PROPERTIES_TEMPLATE.format(
        signing_time=signing_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        cert_digest=_certificate_digest(certificate_b64),
        issuer_name=issuer,
        serial_number=str(certificate.serial_number),
    )


def sign_invoice_hash(private_key, invoice_hash):
    """ECDSA-SHA256 over the raw digest bytes of the invoice hash."""
    digest = base64.b64decode(invoice_hash)
    signature = private_key.sign(digest, ec.ECDSA(hashes.SHA256()))
    return base64.b64encode(signature).decode()


def stamp_invoice(xml_string, invoice_hash, certificate_b64, private_key, signing_time):
    """Embed the XAdES B-B stamp and return (signed_xml, signature_b64)."""
    signature_b64 = sign_invoice_hash(private_key, invoice_hash)
    signed_properties = _signed_properties(certificate_b64, signing_time)
    signed_properties_hash = base64.b64encode(
        hashlib.sha256(signed_properties.encode()).hexdigest().encode()
    ).decode()
    extensions = _UBL_EXTENSIONS_TEMPLATE.format(
        invoice_hash=invoice_hash,
        signed_properties_hash=signed_properties_hash,
        signature_value=signature_b64,
        certificate=certificate_b64,
        signed_properties=signed_properties,
    )
    parser = etree.XMLParser(remove_blank_text=False, resolve_entities=False)
    root = etree.fromstring(xml_string.encode(), parser=parser)
    root.insert(0, etree.fromstring(extensions.encode(), parser=parser))
    # The UBL signature placeholder that ds:Signature references. UBL 2.1
    # element order puts cac:Signature directly before the supplier party.
    signature_block = etree.Element(f"{{{CAC}}}Signature")
    _sub(
        signature_block,
        CBC,
        "ID",
        "urn:oasis:names:specification:ubl:signature:Invoice",
    )
    _sub(
        signature_block,
        CBC,
        "SignatureMethod",
        "urn:oasis:names:specification:ubl:dsig:enveloped:xades",
    )
    supplier = root.find(f"{{{CAC}}}AccountingSupplierParty")
    supplier.addprevious(signature_block)
    return (
        etree.tostring(root, xml_declaration=True, encoding="UTF-8").decode(),
        signature_b64,
    )


def embed_qr(xml_string, qr_b64):
    """Insert the QR AdditionalDocumentReference after the PIH reference."""
    parser = etree.XMLParser(remove_blank_text=False, resolve_entities=False)
    root = etree.fromstring(xml_string.encode(), parser=parser)
    references = root.xpath("//cac:AdditionalDocumentReference", namespaces=_XPATH_NS)
    anchor = references[-1]
    qr_ref = etree.Element(f"{{{CAC}}}AdditionalDocumentReference")
    _sub(qr_ref, CBC, "ID", "QR")
    attachment = _sub(qr_ref, CAC, "Attachment")
    _sub(
        attachment,
        CBC,
        "EmbeddedDocumentBinaryObject",
        qr_b64,
        mimeCode="text/plain",
    )
    anchor.addnext(qr_ref)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8").decode()


def certificate_public_key_der(certificate_b64):
    certificate = x509.load_der_x509_certificate(base64.b64decode(certificate_b64))
    return certificate.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def certificate_signature_bytes(certificate_b64):
    """The CA's signature over the device certificate — QR tag 9."""
    certificate = x509.load_der_x509_certificate(base64.b64decode(certificate_b64))
    return certificate.signature
