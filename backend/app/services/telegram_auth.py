import hmac, hashlib, urllib.parse
from typing import Dict, Any

from ..config import settings

def _parse_init_data(init_data: str) -> Dict[str, str]:
    parsed = dict(urllib.parse.parse_qsl(init_data, strict_parsing=True))
    return parsed

def verify_telegram_init_data(init_data: str, bot_token: str) -> Dict[str, Any]:
    """
    Returns user dict if valid.
    DEV MODE: allow empty init_data or "dev" when ALLOW_DEV_AUTH is enabled.
    """
    if settings.ALLOW_DEV_AUTH and (not init_data or init_data == "dev"):
        return {"id": settings.DEV_USER_ID, "first_name": "Dev", "last_name": "User", "username": "dev_user"}

    data = _parse_init_data(init_data)
    if "hash" not in data:
        raise ValueError("Missing hash")

    received_hash = data.pop("hash")
    pairs = [f"{k}={v}" for k, v in sorted(data.items())]
    data_check_string = "\n".join(pairs)

    secret_key = hashlib.sha256(bot_token.encode()).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise ValueError("Invalid hash")

    if "user" not in data:
        raise ValueError("Missing user")

    import json
    user = json.loads(data["user"])
    return user
