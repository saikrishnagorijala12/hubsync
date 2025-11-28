from flask import Blueprint, session, redirect, url_for, request, render_template
from hubsync.service.auth import _build_auth_url,_build_msal_app,REDIRECT_PATH,AUTHORITY,SCOPE
import uuid


auth_bp = Blueprint('auth', __name__, url_prefix='/')


@auth_bp.route('/')
def index():
    if session.get("user"):
        return render_template("profile.html", user=session["user"])
    return render_template("index.html")


@auth_bp.route('/profile')
def profile():
    if session.get("user"):
        print(session.get("user"))
        return render_template("profile.html", user=session["user"])
    else: 
        return redirect(url_for("auth.index"))

@auth_bp.route("/login")
def login():
    session["state"] = str(uuid.uuid4())
    auth_url = _build_auth_url(state=session["state"])
    return redirect(auth_url)


@auth_bp.route(REDIRECT_PATH)
def authorized():
    if request.args.get("state") != session.get("state"):
        return redirect(url_for("auth.index"))

    if "error" in request.args:
        return f"Error: {request.args.get('error_description', request.args.get('error'))}"

    code = request.args.get("code")
    if not code:
        return "No code returned by the auth server.", 400

    result = _build_msal_app().acquire_token_by_authorization_code(
        code,
        scopes=SCOPE,
        redirect_uri=url_for("auth.authorized", _external=True) 
    )

 
    print("MSAL RESULT:", result)

    if result.get("id_token_claims"):
        session["user"] = result["id_token_claims"]
        return redirect(url_for("auth.index"))
    else:
        return f"Login failed. Details: {result.get('error_description', result)}", 400


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(
        f"{AUTHORITY}/oauth2/v2.0/logout?post_logout_redirect_uri={url_for('auth.index', _external=True)}"
    )



