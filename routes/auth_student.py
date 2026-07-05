import re

from flask import Blueprint, render_template, request, session, redirect, url_for
from werkzeug.security import check_password_hash

from utils.db import fetch_one

bp_auth_student = Blueprint("bp_auth_student", __name__)


def _validate_student_username(username: str) -> bool:
    # Expected format: studentname_dateofbirth (basic format check)
    # e.g. "student_john_2005-01-31" or "studentjohn_20050131" depending on future.
    # We'll require at least one '_' and a date-like suffix.
    if not username:
        return False
    if "_" not in username:
        return False
    # date tail: allow YYYY-MM-DD, YYYYMMDD, YYYY/MM/DD
    return re.search(r"(\d{4}[-/]?\d{2}[-/]?\d{2}|\d{8})$", username) is not None


@bp_auth_student.route("/student/login", methods=["GET", "POST"])
def login_student():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if not username or not password:
            return render_template(
                "login_student.html", error="Username and password are required"
            )

        if not _validate_student_username(username):
            return render_template(
                "login_student.html",
                error="Invalid student username format. Expected: studentname_dateofbirth",
            )

        row = fetch_one(
            "SELECT id, username, password, full_name FROM students WHERE username=%s",
            (username,),
        )
        if row and check_password_hash(row["password"], password):
            session.clear()
            session["user"] = row["id"]
            session["role"] = "student"
            session["username"] = row["username"]
            session["full_name"] = row["full_name"]
            return redirect(url_for("bp_student.dashboard"))


        return render_template("login_student.html", error="Invalid credentials")

    return render_template("login_student.html")


