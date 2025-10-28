import base64
import json
from datetime import datetime, timezone
from typing import Any, Dict

def decode_jwt(token: str) -> Dict[str, Any]:
    """
    Dekoduje token JWT (bez weryfikacji podpisu).
    Zwraca dict z payloadem.
    """
    if not token:
        raise ValueError("Token jest pusty")

    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Niepoprawny format JWT")

        # interesuje nas druga część (payload)
        payload_b64 = parts[1]
        # dodaj padding '=' jeśli brakuje
        rem = len(payload_b64) % 4
        if rem:
            payload_b64 += "=" * (4 - rem)

        decoded_bytes = base64.urlsafe_b64decode(payload_b64)
        decoded_str = decoded_bytes.decode("utf-8")
        return json.loads(decoded_str)
    except Exception as e:
        raise ValueError(f"Nie udało się zdekodować JWT: {e}") from e


def iso_utc(dt: datetime) -> str:
    """
    Zwraca czas w formacie ISO8601 w UTC bez mikrosekund, z sufiksem 'Z'.
    """
    dt_utc = dt.astimezone(timezone.utc).replace(microsecond=0)
    return dt_utc.isoformat().replace("+00:00", "Z")
