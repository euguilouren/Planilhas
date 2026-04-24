"""JWT HS256 mínimo usando apenas stdlib — sem dependência de PyJWT ou cryptography."""

import base64
import hashlib
import hmac
import json
import time
from typing import Any


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * (padding % 4))


def encode(payload: dict[str, Any], secret: str) -> str:
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header}.{body}".encode()
    sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    return f"{header}.{body}.{_b64url_encode(sig)}"


def decode(token: str, secret: str) -> dict[str, Any]:
    """Decodifica e valida assinatura + expiração. Levanta ValueError em caso de erro."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Token malformado")
    header_b64, body_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{body_b64}".encode()
    expected_sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    received_sig = _b64url_decode(sig_b64)
    if not hmac.compare_digest(expected_sig, received_sig):
        raise ValueError("Assinatura inválida")
    payload: dict[str, Any] = json.loads(_b64url_decode(body_b64))
    exp = payload.get("exp")
    if exp is not None and time.time() > exp:
        raise ValueError("Token expirado")
    return payload
