from flask import Blueprint, render_template, session

from utils.auth import login_required
from utils.db import fetch_one

bp_student = Blueprint("bp_student", __name__)


@bp_student.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    if session.get("role") != "student":
        return render_template("roles.html")

    student_id = session.get("user")

    # Fetch student profile details to display on dashboard
    row = fetch_one(
        """
        SELECT id, full_name, username, roll_number, date_of_birth
        FROM students
        WHERE id=%s
        """,
        (student_id,),
    )

    return render_template(
        "student/dashboard.html",
        student=row,
        full_name=session.get("full_name"),
        username=session.get("username"),
        roll_number=(row.get("roll_number") if row else None),
    )


