import re

# --- GLOBAL CONFIGURATION FLAG ---
# False: Keeps mock data human-readable for local development/demos
# True:  Enforces strict PII redaction before LLM API calls (GDPR/LGPD mode)
ENABLE_PII_MASKING = False


class SecuritySanitizer:
    """Security layer for handling PII and customer identity protection."""

    @staticmethod
    def sanitize_customer_profile(customer_dict: dict) -> dict:
        """
        Masks structured customer attributes if PII masking is enabled.
        """
        if not ENABLE_PII_MASKING:
            return customer_dict  # Return raw profile for local mock testing

        sanitized = customer_dict.copy()
        if "full_name" in sanitized:
            customer_id = sanitized.get("customer_id", "UNKNOWN")
            sanitized["full_name"] = f"ANON_USER_{customer_id}"

        return sanitized

    @staticmethod
    def redact_pii_from_text(text: str, customer_name: str = None) -> str:
        """
        Redacts emails, phone numbers, CPFs, and customer names if PII masking is enabled.
        """
        if not text or not ENABLE_PII_MASKING:
            return text  # Return raw text for local mock testing

        # 1. Dynamically redact customer name if provided
        if customer_name and len(customer_name.strip()) > 2:
            text = re.sub(
                re.escape(customer_name),
                "[REDACTED NAME]",
                text,
                flags=re.IGNORECASE,
            )

            # Redact first name separately
            first_name = customer_name.split()[0]
            if len(first_name) > 2:
                text = re.sub(
                    rf"\b{re.escape(first_name)}\b",
                    "[REDACTED NAME]",
                    text,
                    flags=re.IGNORECASE,
                )

        # 2. Redact Emails
        text = re.sub(
            r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
            "[REDACTED EMAIL]",
            text,
        )

        # 3. Redact Phone Numbers
        text = re.sub(
            r"\b(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?(?:9?\d{4}[-.\s]?\d{4})\b",
            "[REDACTED PHONE]",
            text,
        )

        # 4. Redact Brazilian CPFs
        text = re.sub(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", "[REDACTED CPF]", text)

        return text


# --- Quick Test Execution ---
if __name__ == "__main__":
    sample_name = "Alice Smith"
    sample_profile = {"customer_id": 101, "full_name": sample_name, "credit_score": 580}
    sample_log = "Customer Alice Smith (alice@example.com, CPF: 123.456.789-00) requested a payment extension."

    print(f"Current Security State: ENABLE_PII_MASKING = {ENABLE_PII_MASKING}\n")

    print("Profile Output:", SecuritySanitizer.sanitize_customer_profile(sample_profile))
    print("Log Output:    ", SecuritySanitizer.redact_pii_from_text(sample_log, customer_name=sample_name))