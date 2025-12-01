from flask import url_for, current_app
from msal import ConfidentialClientApplication


def _get_config():
    """Retrieve Azure identity settings from Flask config."""
    config = current_app.config
    return {
        "client_id": config.get("CLIENT_ID"),
        "client_secret": config.get("CLIENT_SECRET"),
        "tenant_id": config.get("TENANT_ID"),
        "scope": config.get("SCOPE", ["User.Read"]),
        "redirect_path": config.get("REDIRECT_PATH", "/getAToken"),
        "authority": f"https://login.microsoftonline.com/{config.get('TENANT_ID')}"
    }


def _build_msal_app(cache=None):
    config = _get_config()
    return ConfidentialClientApplication(
        config["client_id"],
        authority=config["authority"],
        client_credential=config["client_secret"],
        token_cache=cache
    )


def _build_auth_url(state=None):
    config = _get_config()

    return _build_msal_app().get_authorization_request_url(
        config["scope"],
        state=state,
        redirect_uri=url_for("auth.authorized", _external=True)
    )
