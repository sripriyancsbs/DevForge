import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from app.core.config import settings

# OWASP Recommended iterations for PBKDF2-HMAC-SHA256
PBKDF2_ITERATIONS = 600000
SALT_SIZE = 16


def hash_password(password: str) -> str:
    """
    Securely hash a password using NIST SP 800-132 / OWASP recommended
    PBKDF2-HMAC-SHA256 with 600,000 rounds and a random 16-byte cryptographic salt.
    """
    if not password:
        raise ValueError("Password cannot be empty")
    salt = secrets.token_bytes(SALT_SIZE)
    pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${pw_hash.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored PBKDF2-HMAC-SHA256 hash
    using constant-time comparison to prevent timing attacks.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        parts = hashed_password.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_hash = parts[3]
        calculated_hash = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations).hex()
        return secrets.compare_digest(expected_hash, calculated_hash)
    except Exception:
        return False


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(s: str) -> bytes:
    rem = len(s) % 4
    if rem > 0:
        s += "=" * (4 - rem)
    return base64.urlsafe_b64decode(s.encode("utf-8"))


def create_access_token(
    subject: str,
    username: str,
    role: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a signed RFC 7519 HS256 JWT access token.
    """
    now = int(time.time())
    if expires_delta:
        exp = now + int(expires_delta.total_seconds())
    else:
        exp = now + (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(subject),
        "username": username,
        "role": role.upper(),
        "iat": now,
        "exp": exp,
        "iss": "devforge-auth"
    }

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

    secret_bytes = settings.SECRET_KEY.encode("utf-8")
    signature = hmac.new(secret_bytes, signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify signature and decode a signed HS256 JWT token.
    Returns the payload dictionary or None if invalid or expired.
    """
    if not token or not token.strip():
        return None

    clean_token = token.strip()
    if clean_token.lower().startswith("bearer "):
        clean_token = clean_token[7:].strip()

    parts = clean_token.split(".")
    if len(parts) != 3:
        return None

    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    secret_bytes = settings.SECRET_KEY.encode("utf-8")

    expected_sig = _b64url_encode(hmac.new(secret_bytes, signing_input, hashlib.sha256).digest())
    if not secrets.compare_digest(sig_b64, expected_sig):
        return None

    try:
        payload_bytes = _b64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
        # Verify expiration
        exp = payload.get("exp")
        if exp is not None and time.time() > float(exp):
            return None
        return payload
    except Exception:
        return None


# Patterns for sensitive tokens and passwords
SECRET_PATTERNS = [
    re.compile(r"(password['\":\s=]+)(['\"]?)([^'\"\s&,]+)\2", re.IGNORECASE),
    re.compile(r"(bearer\s+)([a-zA-Z0-9_\-\.]+)", re.IGNORECASE),
    re.compile(r"(token['\":\s=]+)(['\"]?)([^'\"\s&,]+)\2", re.IGNORECASE),
    re.compile(r"(secret['\":\s=]+)(['\"]?)([^'\"\s&,]+)\2", re.IGNORECASE),
    re.compile(r"(ghp_[a-zA-Z0-9]{36,})", re.IGNORECASE),
]


def mask_secret(text: str) -> str:
    """Mask credentials and secrets in logs or audit outputs."""
    if not text:
        return ""
    result = text
    for pattern in SECRET_PATTERNS:
        if pattern.groups == 1:
            result = pattern.sub(r"***REDACTED***", result)
        elif pattern.groups == 2:
            result = pattern.sub(r"\1***REDACTED***", result)
        elif pattern.groups >= 3:
            result = pattern.sub(r"\1\2***REDACTED***\2", result)
    return result
