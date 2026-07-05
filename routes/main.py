from flask import Blueprint, render_template, redirect, url_for

bp_main = Blueprint("bp_main", __name__)


@bp_main.route("/", methods=["GET"])
def welcome():
    return render_template("welcome.html")


@bp_main.route("/get-started", methods=["GET"])
def get_started():
    # clear session optionally
    return render_template("roles.html")

