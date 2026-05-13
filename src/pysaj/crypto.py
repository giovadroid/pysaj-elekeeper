"""Crypto and signing helpers for the Elekeeper API."""

from __future__ import annotations

import hashlib
import random
from collections.abc import Mapping
from datetime import date
from typing import Any

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

APP_PROJECT_NAME = "elekeeper"
CLIENT_ID = "esolar-monitor-admin"
SIGNATURE_SECRET = "ktoKRLgQPjvNyUZO8lVc9kU1Bsip6XIe"
PASSWORD_AES_KEY_HEX = "ec1840a7c53cf0709eb784be480379b6"
RANDOM_ALPHABET = "ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678"


def encrypt_password(password: str) -> str:
    """Encrypt a plaintext password the same way the Elekeeper frontend does."""

    cipher = AES.new(bytes.fromhex(PASSWORD_AES_KEY_HEX), AES.MODE_ECB)
    return cipher.encrypt(pad(password.encode("utf-8"), AES.block_size)).hex()


def random_token(length: int = 32) -> str:
    """Generate the request random field using the frontend alphabet."""

    return "".join(random.choice(RANDOM_ALPHABET) for _ in range(length))


def is_empty(value: Any) -> bool:
    """Match the frontend's removal of empty request fields."""

    return value is None or value == "" or value == [] or value == {}


def compact_mapping(values: Mapping[str, Any]) -> dict[str, Any]:
    """Drop empty values recursively where the frontend does so."""

    compacted: dict[str, Any] = {}
    for key, value in values.items():
        if isinstance(value, Mapping):
            value = compact_mapping(value)
        elif isinstance(value, list):
            value = [item for item in value if not is_empty(item)]
        if not is_empty(value):
            compacted[key] = value
    return compacted


def common_params(*, language: str = "en") -> dict[str, Any]:
    """Return common request parameters added by the Elekeeper frontend."""

    return {
        "appProjectName": APP_PROJECT_NAME,
        "clientDate": date.today().isoformat(),
        "lang": language,
        "timeStamp": _timestamp_ms(),
        "random": random_token(),
    }


def signed_params(
    params: Mapping[str, Any] | None = None,
    *,
    language: str = "en",
    sign_only_common: bool = False,
) -> dict[str, Any]:
    """Return params with common fields and Elekeeper signature fields.

    Login requests sign only the common fields. Most API calls sign the full
    request payload plus common fields.
    """

    common = common_params(language=language)
    request_params = compact_mapping({**(params or {}), **common})
    signature_source = compact_mapping(common if sign_only_common else dict(request_params))

    signature_source.pop("confirmPassword", None)
    signature_source.pop("rememberMe", None)
    signature_source.pop("uuid", None)
    signature_source["clientId"] = CLIENT_ID

    keys = list(signature_source)
    canonical = "&".join(
        sorted(f"{key}={signature_source[key]}" for key in keys)
    )
    md5_hex = hashlib.md5(
        f"{canonical}&key={SIGNATURE_SECRET}".encode(), usedforsecurity=False
    ).hexdigest()
    signature = hashlib.sha1(md5_hex.encode("utf-8"), usedforsecurity=False).hexdigest().upper()

    return {
        **request_params,
        "appProjectName": APP_PROJECT_NAME,
        "clientId": CLIENT_ID,
        "signParams": ",".join(keys),
        "signature": signature,
        "timeStamp": common["timeStamp"],
        "clientDate": common["clientDate"],
        "random": common["random"],
    }


def _timestamp_ms() -> int:
    from time import time

    return int(time() * 1000)
