SENSITIVE_KEY_PARTS = frozenset(
    {
        "authorization",
        "credential",
        "password",
        "private_key",
        "secret",
        "token",
    }
)


def is_sensitive_key(key: object) -> bool:
    normalized = str(key).lower().replace("-", "_")
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def contains_sensitive_keys(value: object) -> bool:
    if isinstance(value, dict):
        return any(
            is_sensitive_key(key) or contains_sensitive_keys(item) for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(contains_sensitive_keys(item) for item in value)
    return False


def redact_sensitive(value: object) -> object:
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]" if is_sensitive_key(key) else redact_sensitive(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_sensitive(item) for item in value]
    return value
