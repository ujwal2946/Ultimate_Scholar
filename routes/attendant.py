from flask import Blueprint, render_template, session

from utils.auth import login_required

bp_attendant = Blueprint("bp_attendant", __name__)


@bp_attendant.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    if session.get("role") != "attendant":
        return render_template("roles.html")
    return render_template("attendant/dashboard.html")

