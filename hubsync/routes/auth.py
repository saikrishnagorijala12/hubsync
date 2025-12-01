from flask import Blueprint, session, redirect, url_for, request, render_template, current_app
from ..services.auth import _build_auth_url, _build_msal_app
import uuid

auth_bp = Blueprint("auth", __name__, url_prefix="/")


def _get_config():
    """Read runtime configuration from Flask config."""
    cfg = current_app.config
    return {
        "redirect_path": cfg.get("REDIRECT_PATH", "/getAToken"),
        "authority": f"https://login.microsoftonline.com/{cfg.get('TENANT_ID')}",
        "scope": cfg.get("SCOPE", ["User.Read"]),
    }


@auth_bp.route("/")
def index():
    if "user" in session:
        return render_template("profile.html", user=session["user"])
    return render_template("index.html")


@auth_bp.route("/profile")
def profile():
    if "user" in session:
        return render_template("profile.html", user=session["user"])
    return redirect(url_for("auth.index"))


@auth_bp.route("/login")
def login():
    session["state"] = str(uuid.uuid4())
    auth_url = _build_auth_url(state=session["state"])
    return redirect(auth_url)


@auth_bp.route("/getAToken")  # Dynamic based on config handled below
def authorized():
    cfg = _get_config()

    if request.args.get("state") != session.get("state"):
        return redirect(url_for("auth.index"))

    if "error" in request.args:
        return f"Error: {request.args.get('error_description', request.args.get('error'))}"

    code = request.args.get("code")
    if not code:
        return "No authorization code returned.", 400

    token_result = _build_msal_app().acquire_token_by_authorization_code(
        code,
        scopes=cfg["scope"],
        redirect_uri=url_for("auth.authorized", _external=True),
    )

    if token_result.get("id_token_claims"):
        session["user"] = token_result["id_token_claims"]
        return redirect(url_for("auth.index"))

    return f"Login failed: {token_result.get('error_description', token_result)}", 400


@auth_bp.route("/logout")
def logout():
    cfg = _get_config()

    session.clear()

    return redirect(
        f"{cfg['authority']}/oauth2/v2.0/logout?post_logout_redirect_uri="
        f"{url_for('auth.index', _external=True)}"
    )
