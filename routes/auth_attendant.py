from flask import Blueprint, render_template, request, session, redirect, url_for
from werkzeug.security import check_password_hash

from utils.db import fetch_one

bp_auth_attendant = Blueprint("bp_auth_attendant", __name__)


@bp_auth_attendant.route("/attendant/login", methods=["GET", "POST"])
def login_attendant():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if not username or not password:
            return render_template(
                "login_attendant.html", error="Username and password are required"
            )

        row = fetch_one(
            "SELECT id, username, password FROM attendants WHERE username=%s", (username,)
        )
        if row and check_password_hash(row["password"], password):
            session.clear()
            session["user"] = row["id"]
            session["role"] = "attendant"
            session["username"] = row["username"]
            return redirect(url_for("bp_attendant.dashboard"))


        return render_template("login_attendant.html", error="Invalid credentials")

    return render_template("login_attendant.html")


