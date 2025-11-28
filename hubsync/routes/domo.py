from flask import (
    
    redirect,
    url_for,
    session,
    Blueprint,
    render_template_string,
    jsonify,
    
)
import os,time,requests
from threading import Lock
import json



with open("domo.json", "r") as f:
    data = json.load(f)

domo_bp = Blueprint('domo', __name__, url_prefix='/domo')

DOMO_API_HOST = os.getenv("DOMO_API_HOST")
DOMO_EMBED_HOST = os.getenv("DOMO_EMBED_HOST")
DOMO_CLIENT_ID = os.getenv("DOMO_CLIENT_ID")
DOMO_CLIENT_SECRET = os.getenv("DOMO_CLIENT_SECRET")
CARD_DASHBORD=os.getenv("C_D")

DOMO_TOKEN_CACHE = {"access_token": None, "expires_at": 0}
_DOMO_TOKEN_LOCK = Lock()

def get_domo_access_token(scopes: str = "data user dashboard"):
    """
    Request Domo OAuth token using client_credentials.
    Process-memory cache. Use Redis or similar in production.
    """
    now = time.time()
    with _DOMO_TOKEN_LOCK:
        if DOMO_TOKEN_CACHE["access_token"] and DOMO_TOKEN_CACHE["expires_at"] > now + 5:
            return DOMO_TOKEN_CACHE["access_token"]

        token_url = f"{DOMO_API_HOST}/oauth/token"
        auth = (DOMO_CLIENT_ID, DOMO_CLIENT_SECRET)
        headers = {"Accept": "application/json"}
        data = {"grant_type": "client_credentials", "scope": scopes}

        r = requests.post(token_url, auth=auth, data=data, headers=headers, timeout=10)
        r.raise_for_status()
        j = r.json()
        access_token = j.get("access_token")
        expires_in = int(j.get("expires_in", 300))

        DOMO_TOKEN_CACHE["access_token"] = access_token
        DOMO_TOKEN_CACHE["expires_at"] = time.time() + expires_in
        return access_token


def create_domo_embed_token(access_token: str, embed_id: str, session_length_minutes: int = 60):
    """
    Request an embed token from the Domo API.
    Make sure embed_id is valid and the Domo client has access.
    """
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
    return r.json().get("authentication")



def is_logged_in():
    return "user" in session



@domo_bp.route("/api/me")
def api_me():
    if not is_logged_in():
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"user": session["user"]})


def choose_embed_page_for_user(user):
    """
    Return the embed page id to use for this user.
    Replace this logic with your real mapping (DB, roles, groups, etc).
    """
    

    for entry in data:
        if entry["email"] == user.get("preferred_username"):
            return entry["embed_id"]


@domo_bp.route("/embed-page")
def embed_page():
    if not is_logged_in():
        return redirect(url_for("login"))

    user = session.get("user")
    page_id = choose_embed_page_for_user(user)
    if not page_id:
        return render_template_string("<h3>No embed page configured for this user</h3>"), 500

    try:
        access_token = get_domo_access_token()
        embed_token = create_domo_embed_token(access_token, page_id, session_length_minutes=60)
        if not embed_token:
            raise RuntimeError("Domo did not return an embed token")
    except Exception as e:
        return render_template_string("<h3>Error creating Domo embed token</h3><pre>{{err}}</pre>", err=str(e)), 500

    html = f"""
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8" />
        <title>Domo Embed</title>
        <style>html,body,iframe{{height:100%;margin:0;padding:0;border:0}} iframe{{width:100%}}</style>
      </head>
      <body>
        <form id="domoForm" action="{DOMO_EMBED_HOST}/embed/pages/{page_id}" method="post" target="domoFrame">
          <input type="hidden" name="embedToken" value="{embed_token}" />
        </form>
        <iframe name="domoFrame" id="domoFrame" frameborder="0" allowfullscreen></iframe>
        <script>document.getElementById('domoForm').submit();</script>
      </body>
    </html>
    """
    return render_template_string(html)


@domo_bp.route("/domo/embed-token")
def domo_embed_token_api():
    if not is_logged_in():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        access_token = get_domo_access_token()
        page_id = choose_embed_page_for_user(session.get("user"))
        embed_token = create_domo_embed_token(access_token, page_id, session_length_minutes=60)
        if not embed_token:
            raise RuntimeError("Domo did not return an embed token")
        return jsonify({"embedToken": embed_token})
    except Exception as e:
        return jsonify({"error": "failed to create embed token", "detail": str(e)}), 500



def domo_create_user(access_token: str, email: str, first_name: str = "", last_name: str = "", role: str = "Participant"):
    """
    Example helper to create a user in Domo via API.
    NOTE: check Domo Admin API docs for exact payload and endpoint.
    This is a template showing how you'd call the users API.
    """
    
    users_endpoint = f"{DOMO_API_HOST}/v1/users"  
    payload = {
        "email": email,
        "firstName": first_name,
        "lastName": last_name,
        "role": role,  
    }
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    r = requests.post(users_endpoint, headers=headers, json=payload, timeout=10)
    r.raise_for_status()
    return r.json()
