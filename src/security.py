import re
from config import ENABLE_PII_MASKING
from typing import Optional


class SecuritySanitizer:
    """Handles structured masking and dynamic regex redaction of customer PII."""

    def __init__(self, enable_masking: bool = ENABLE_PII_MASKING):
        self.enable_masking = enable_masking

    def sanitize_customer_profile(self, customer_data: dict) -> dict:
        """Masks structured customer attributes if PII masking is enabled."""
        if not self.enable_masking or not customer_data:
            return customer_data

        sanitized = customer_data.copy()
        cust_id = sanitized.get("customer_id", "UNKNOWN")

        # Anonymize identifiable structured attributes
        sanitized["full_name"] = f"ANON_USER_{cust_id}"
        if "email" in sanitized:
            sanitized["email"] = f"anon_user_{cust_id}@masked-domain.com"
        if "phone" in sanitized:
            sanitized["phone"] = "[REDACTED PHONE]"
        if "cpf" in sanitized:
            sanitized["cpf"] = "[REDACTED CPF]"

        return sanitized

    def redact_pii_from_text(self, text: str, target_name: Optional[str] = None) -> str:
        """Redacts unstructured PII (CPFs, Emails, Phones, Names) from text logs."""
        if not self.enable_masking or not text:
            return text

        # 1. Redact Brazilian CPFs
        text = re.sub(
            r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b\d{11}\b",
            "[REDACTED CPF]",
            text,
        )

        # 2. Redact Emails
        text = re.sub(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
            "[REDACTED EMAIL]",
            text,
        )

        # 3. Redact Phone Numbers (Brazilian & International Formats)
        text = re.sub(
            r"\b(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?(?:9?\d{4}[-.\s]?\d{4})\b",
            "[REDACTED PHONE]",
            text,
        )

        # 4. Context-Aware Name Redaction
        if target_name and target_name.strip():
            # Redact full name
            text = re.sub(
                re.escape(target_name.strip()),
                "[REDACTED NAME]",
                text,
                flags=re.IGNORECASE,
            )
            # Redact standalone first name
            first_name = target_name.strip().split()[0]
            if len(first_name) > 2:
                text = re.sub(
                    r"\b" + re.escape(first_name) + r"\b",
                    "[REDACTED NAME]",
                    text,
                    flags=re.IGNORECASE,
                )

        return text


if __name__ == "__main__":
    from database import fetch_customer_by_id

    sanitizer = SecuritySanitizer()
    print(f"Current System Mode: ENABLE_PII_MASKING = {sanitizer.enable_masking}\n")

    raw_customer = fetch_customer_by_id(101)

    if raw_customer:
        clean_profile = sanitizer.sanitize_customer_profile(raw_customer)
        clean_notes = sanitizer.redact_pii_from_text(
            text=raw_customer.get("notes", ""),
            target_name=raw_customer.get("full_name"),
        )

        print("=== INPUT RAW DATA (DuckDB) ===")
        print(f"Name:  {raw_customer['full_name']}")
        print(f"Notes: {raw_customer['notes']}\n")

        print("=== OUTPUT FOR LLM AGENT ===")
        print(f"Name:  {clean_profile['full_name']}")
        print(f"Notes: {clean_notes}")