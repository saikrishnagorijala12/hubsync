from flask import Blueprint, jsonify, render_template, render_template_string, redirect, url_for, session
from ..services.domo import (
    is_logged_in,
    get_embed_ids_for_user,
    get_embed_configuration,
    get_access_token,
    create_embed_token
)

domo_bp = Blueprint("domo", __name__, url_prefix="/domo")


@domo_bp.route("/embed-page")
def embed_page():
    if not is_logged_in():
        return redirect(url_for("login"))

    config = get_embed_configuration()

    if not config:
        return render_template_string("<h3>No embed pages configured for this user</h3>"), 404

    embeds, host = config
    return render_template("domo_embed.html", embeds=embeds, host=host)


@domo_bp.route("/embed-token")
def embed_token_api():
    if not is_logged_in():
        return jsonify({"error": "Unauthorized"}), 401

    embed_ids = get_embed_ids_for_user()
    if not embed_ids:
        return jsonify({"error": "No embed pages configured for this user"}), 404

    try:
        access = get_access_token()
        tokens = [
            {"embed_id": eid, "embedToken": create_embed_token(access, eid)}
            for eid in embed_ids
        ]

        return jsonify({
            "user": session["user"].get("preferred_username"),
            "count": len(tokens),
            "embeds": tokens
        })

    except Exception as e:
        return jsonify({"error": "failed to create embed tokens", "detail": str(e)}), 500
