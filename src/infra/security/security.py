import re

from src.infra.database.database import get_db_connection


def sanitize_input(text: str) -> str:
    """Strips potential prompt injection characters/tags and attack phrases from text."""
    if not isinstance(text, str):
        return ""

    cleaned = re.sub(r"[<>{}\\]", "", text)

    injection_patterns = [
        r"(?i)ignore\s+(?:all\s+|previous\s+|prior\s+|the\s+|above\s+)*instructions.*",
        r"(?i)system\s+prompt.*",
        r"(?i)override\s+(decision|rules).*",
        r"(?i)and\s+return\s+approved.*",
        r"(?i)and\s+approve.*"
    ]

    for pattern in injection_patterns:
        cleaned = re.sub(pattern, "[REDACTED_INJECTION_ATTEMPT]", cleaned)

    return cleaned.strip()


def mask_cpf(cpf: str) -> str:
    """Masks CPF for privacy compliance (e.g., ***.456.789-**)."""
    if not cpf or not isinstance(cpf, str):
        return "N/A"
    digits = re.sub(r"\D", "", cpf)
    if len(digits) == 11:
        return f"***.{digits[3:6]}.{digits[6:9]}-**"
    return "***.***.***-**"


def mask_email(email: str) -> str:
    """Masks email address (e.g., a***e@example.com)."""
    if not email or "@" not in email:
        return "m***d@example.com"
    name, domain = email.split("@", 1)
    if len(name) <= 2:
        masked_name = name[0] + "*"
    else:
        masked_name = name[0] + "*" * (len(name) - 2) + name[-1]
    return f"{masked_name}@{domain}"


def mask_phone(phone: str) -> str:
    """Masks phone number (e.g., +55 11 *****-4321)."""
    if not phone or not isinstance(phone, str):
        return "+55 ** *****-****"
    # Fail closed: an unrecognized format must not be returned in the clear.
    output = re.sub(r"(\+?\d{2}\s?\d{2}\s?)\d{5}(-\d{4})", r"\1*****\2", phone)
    return output if output != phone else "+55 ** *****-****"


_PII_MASKS = {"cpf": mask_cpf, "email": mask_email, "phone_number": mask_phone}
_PII_MASKED_KEYS = {"cpf": "cpf_masked", "email": "email_masked", "phone_number": "phone_masked"}


def masked_pii_view(record: dict) -> dict:
    """Returns `<field>_masked` values for every known PII field present in
    record, e.g. {"cpf_masked": ...}. The record itself is left untouched, so
    callers can expose both the raw and masked value side by side."""
    return {
        _PII_MASKED_KEYS[field]: mask(str(record[field]))
        for field, mask in _PII_MASKS.items()
        if field in record
    }


def get_sanitized_customer_data(customer_id: int) -> dict:
    """Fetches customer record from DuckDB, sanitizes notes, and masks PII."""
    with get_db_connection() as conn:
        result = conn.execute("""
            SELECT customer_id, full_name, cpf, email, phone_number, underwriter_notes, credit_score, debt_to_income_ratio
            FROM customers 
            WHERE customer_id = ?
        """, [customer_id]).fetchone()

    if not result:
        return {}

    data = {
        "customer_id": result[0],
        "full_name": result[1],
        "cpf": mask_cpf(result[2]),
        "email": mask_email(result[3]),
        "phone_number": mask_phone(result[4]),
        "underwriter_notes": sanitize_input(result[5]) if result[5] else "",
        "credit_score": result[6],
        "dti": result[7],
    }

    return data
