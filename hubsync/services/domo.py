import time, json, requests
from threading import Lock
from flask import session, current_app

with open("domo.json", "r") as f:
    domo_user_map = json.load(f)

# Token cache
_token_cache = {"access_token": None, "expires_at": 0}
_token_lock = Lock()


def _get_config():
    """Safely access Flask app config values."""
    config = current_app.config
    return {
        "api_host": config.get("DOMO_API_HOST"),
        "embed_host": config.get("DOMO_EMBED_HOST"),
        "client_id": config.get("DOMO_CLIENT_ID"),
        "client_secret": config.get("DOMO_CLIENT_SECRET"),
        "card_target": config.get("CARD_DASHBOARD", "cards"),
    }


def get_access_token(scopes: str = "data user dashboard"):
    config = _get_config()
    now = time.time()

    with _token_lock:
        if _token_cache["access_token"] and _token_cache["expires_at"] > now + 5:
            return _token_cache["access_token"]

        token_url = f"{config['api_host']}/oauth/token"

        response = requests.post(
            token_url,
            auth=(config["client_id"], config["client_secret"]),
            data={"grant_type": "client_credentials", "scope": scopes},
            headers={"Accept": "application/json"},
            timeout=10
        )
        response.raise_for_status()

        data = response.json()
        _token_cache["access_token"] = data["access_token"]
        _token_cache["expires_at"] = now + int(data.get("expires_in", 300))
        return data["access_token"]


def create_embed_token(access_token, embed_id, session_minutes=60):
    if not embed_id:
        raise ValueError("embed_id is required")

    config = _get_config()

    url = f"{config['api_host']}/v1/{config['card_target']}/embed/auth"
    payload = {
        "sessionLength": session_minutes * 60,
        "authorizations": [
            {
                "token": embed_id,
                "permissions": ["READ", "FILTER", "EXPORT"],
                "filters": []
            }
        ]
    }

    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        json=payload,
        timeout=10
    )

    response.raise_for_status()
    return response.json().get("authentication")


def get_embed_ids_for_user():
    user = session.get("user")
    if not user:
        return []

    email = user.get("preferred_username")
    return [entry["embed_id"] for entry in domo_user_map if entry["email"] == email]


def is_logged_in():
    return "user" in session


def get_embed_configuration():
    config = _get_config()
    embed_ids = get_embed_ids_for_user()
    if not embed_ids:
        return None

    access = get_access_token()
    tokens = [{"id": eid, "token": create_embed_token(access, eid)} for eid in embed_ids]

    return tokens, config["embed_host"]
