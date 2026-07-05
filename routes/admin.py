from datetime import date

from flask import Blueprint, render_template, session

from utils.auth import login_required
from utils.db import fetch_one

bp_admin = Blueprint("bp_admin", __name__)


@bp_admin.route("/dashboard", methods=["GET"])
@login_required
def dashboard():

    # enforce role
    if session.get("role") != "admin":
        return render_template("roles.html")

    today = date.today()

    # Total students count
    row = fetch_one("SELECT COUNT(*) AS cnt FROM students")
    total_students = int(row["cnt"] if row and row.get("cnt") is not None else 0)

    # Attendance aggregates for today
    present_row = fetch_one(
        "SELECT COUNT(*) AS cnt FROM attendance WHERE attendance_date=%s AND status=%s",
        (today, "Present"),
    )
    absent_row = fetch_one(
        "SELECT COUNT(*) AS cnt FROM attendance WHERE attendance_date=%s AND status=%s",
        (today, "Absent"),
    )
    late_row = fetch_one(
        "SELECT COUNT(*) AS cnt FROM attendance WHERE attendance_date=%s AND status=%s",
        (today, "Late"),
    )

    present_today = int(present_row["cnt"] if present_row and present_row.get("cnt") is not None else 0)
    absent_today = int(absent_row["cnt"] if absent_row and absent_row.get("cnt") is not None else 0)
    late_today = int(late_row["cnt"] if late_row and late_row.get("cnt") is not None else 0)

    total_today = present_today + absent_today + late_today
    attendance_percentage = round((present_today / total_today) * 100, 2) if total_today else 0

    # Grades count (total grade entries)
    grades_row = fetch_one("SELECT COUNT(*) AS cnt FROM grades")
    grades_count = int(grades_row["cnt"] if grades_row and grades_row.get("cnt") is not None else 0)

    return render_template(
        "admin/dashboard.html",
        total_students=total_students,
        present_today=present_today,
        absent_today=absent_today,
        attendance_percentage=attendance_percentage,
        grades_count=grades_count,
    )



