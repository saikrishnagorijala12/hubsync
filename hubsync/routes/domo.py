from flask import (
    redirect,
    render_template,
    url_for,
    session,
    Blueprint,
    render_template_string,
    jsonify,
)
import os, time, requests
from threading import Lock
import json


with open("domo.json", "r") as f:
    data = json.load(f)

domo_bp = Blueprint('domo', __name__, url_prefix='/domo')

DOMO_API_HOST = os.getenv("DOMO_API_HOST")
DOMO_EMBED_HOST = os.getenv("DOMO_EMBED_HOST")
DOMO_CLIENT_ID = os.getenv("DOMO_CLIENT_ID")
DOMO_CLIENT_SECRET = os.getenv("DOMO_CLIENT_SECRET")
CARD_DASHBORD = os.getenv("C_D")

DOMO_TOKEN_CACHE = {"access_token": None, "expires_at": 0}
_DOMO_TOKEN_LOCK = Lock()


# ---------------------------
# AUTH TOKEN HANDLING
# ---------------------------
def get_domo_access_token(scopes: str = "data user dashboard"):
    now = time.time()
    with _DOMO_TOKEN_LOCK:
        # Use cache if token still valid
        if DOMO_TOKEN_CACHE["access_token"] and DOMO_TOKEN_CACHE["expires_at"] > now + 5:
            return DOMO_TOKEN_CACHE["access_token"]

        token_url = f"{DOMO_API_HOST}/oauth/token"
        auth = (DOMO_CLIENT_ID, DOMO_CLIENT_SECRET)
        headers = {"Accept": "application/json"}
        data = {"grant_type": "client_credentials", "scope": scopes}

        r = requests.post(token_url, auth=auth, data=data, headers=headers, timeout=10)
        r.raise_for_status()
        j = r.json()
        #print(r.json)

        access_token = j.get("access_token")
        expires_in = int(j.get("expires_in", 300))

        DOMO_TOKEN_CACHE["access_token"] = access_token
        DOMO_TOKEN_CACHE["expires_at"] = time.time() + expires_in

        return access_token


# ---------------------------
# EMBED TOKEN CREATION
# ---------------------------
def create_domo_embed_token(access_token: str, embed_id: str, session_length_minutes: int = 60):
    if not embed_id:
        raise ValueError("embed_id is required")

    embed_token_url = f"{DOMO_API_HOST}/v1/{CARD_DASHBORD}/embed/auth"
    payload = {
        "sessionLength": session_length_minutes * 60,
        "authorizations": [
            {
                "token": embed_id,
                "permissions": ["READ", "FILTER", "EXPORT"],
                "filters": []
            }
        ]
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    r = requests.post(embed_token_url, headers=headers, json=payload, timeout=10)
    r.raise_for_status()
    # print(r.json().get("authentication"))

    return r.json().get("authentication")


# ---------------------------
# HELPERS
# ---------------------------
def is_logged_in():
    return "user" in session


@domo_bp.route("/api/me")
def api_me():
    if not is_logged_in():
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"user": session["user"]})


def choose_embed_pages_for_user(user):
    """Return list of embed pages for logged-in user."""
    user_email = user.get("preferred_username")
    return [entry["embed_id"] for entry in data if entry["email"] == user_email]


# ---------------------------
# MULTI-IFRAME EMBED RENDER
# ---------------------------
@domo_bp.route("/embed-page")
def embed_page():
    if not is_logged_in():
        return redirect(url_for("login"))

    user = session.get("user")
    page_ids = choose_embed_pages_for_user(user)

    if not page_ids:
        return render_template_string("<h3>No embed pages configured for this user</h3>"), 404

    try:
        access_token = get_domo_access_token()
        embeds = [
            {"id": page_id, "token": create_domo_embed_token(access_token, page_id, 60)}
            for page_id in page_ids
        ]
    except Exception as e:
        return render_template_string("<h3>Error generating embed tokens</h3><pre>{{err}}</pre>", err=str(e)), 500

    return render_template("domo_embed.html", embeds=embeds, host=DOMO_EMBED_HOST)


# ---------------------------
# MULTI-TOKEN API ENDPOINT
# ---------------------------
@domo_bp.route("/domo/embed-token")
def domo_embed_token_api():
    if not is_logged_in():
        return jsonify({"error": "Unauthorized"}), 401

    try:
        user = session.get("user")
        page_ids = choose_embed_pages_for_user(user)

        if not page_ids:
            return jsonify({"error": "No embed pages configured for this user"}), 404

        access_token = get_domo_access_token()

        embed_list = [
            {"embed_id": page_id, "embedToken": create_domo_embed_token(access_token, page_id, 60)}
            for page_id in page_ids
        ]

        return jsonify({
            "user": user.get("preferred_username"),
            "count": len(embed_list),
            "embeds": embed_list
        })

    except Exception as e:
        return jsonify({"error": "failed to create embed tokens", "detail": str(e)}), 500


# ---------------------------
# USER CREATION (OPTIONAL)
# ---------------------------
# def domo_create_user(access_token: str, email: str, first_name: str = "", last_name: str = "", role: str = "Participant"):
#     users_endpoint = f"{DOMO_API_HOST}/v1/users"
#     payload = {"email": email, "firstName": first_name, "lastName": last_name, "role": role}
#     headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

#     r = requests.post(users_endpoint, headers=headers, json=payload, timeout=10)
#     r.raise_for_status()
#     return r.json()
