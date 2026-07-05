from flask import Blueprint, redirect, url_for, session

bp_logout = Blueprint("bp_logout", __name__)


@bp_logout.route("/logout", methods=["POST", "GET"])
def logout():
    session.clear()
    return redirect(url_for("bp_main.welcome"))


