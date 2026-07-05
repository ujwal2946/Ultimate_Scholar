from datetime import date, datetime

from flask import Blueprint, render_template, session

from utils.auth import login_required, role_required
from utils.db import fetch_one


bp_attendance_student = Blueprint("bp_attendance_student", __name__)


def _today():
    return date.today()


@bp_attendance_student.route("/dashboard", methods=["GET"])
@login_required
@role_required("student")
def dashboard():
    student_id = session.get("user")

    # totals
    totals = fetch_one(
        """
        SELECT status, COUNT(*) AS cnt
        FROM attendance
        WHERE student_id=%s
        GROUP BY status
        """,
        (student_id,),
    )

    present = fetch_one(
        "SELECT COUNT(*) AS cnt FROM attendance WHERE student_id=%s AND status=%s",
        (student_id, "Present"),
    )
    absent = fetch_one(
        "SELECT COUNT(*) AS cnt FROM attendance WHERE student_id=%s AND status=%s",
        (student_id, "Absent"),
    )
    late = fetch_one(
        "SELECT COUNT(*) AS cnt FROM attendance WHERE student_id=%s AND status=%s",
        (student_id, "Late"),
    )

    present_cnt = int(present["cnt"] if present else 0)
    absent_cnt = int(absent["cnt"] if absent else 0)
    late_cnt = int(late["cnt"] if late else 0)

    total = present_cnt + absent_cnt + late_cnt
    attendance_percentage = round((present_cnt / total) * 100, 2) if total else 0

    # absent dates list (for calendar)
    from utils.db import get_connection
    conn = get_connection()
    absent_dates = []
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT attendance_date
                FROM attendance
                WHERE student_id=%s AND status=%s
                ORDER BY attendance_date DESC
                LIMIT 60
                """,
                (student_id, "Absent"),
            )
            rows = cur.fetchall()
            absent_dates = [r["attendance_date"].isoformat() if hasattr(r["attendance_date"], "isoformat") else str(r["attendance_date"]) for r in rows]
    finally:
        conn.close()

    return render_template(
        "student/attendance/dashboard.html",
        attendance_percentage=attendance_percentage,
        total_present=present_cnt,
        total_absent=absent_cnt,
        total_late=late_cnt,
        absent_dates=absent_dates,
    )


@bp_attendance_student.route("/history", methods=["GET"])
def history():
    student_id = session.get("user")
    # history list (simple)
    from utils.db import get_connection
    conn = get_connection()
    rows = []
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT attendance_date, status
                FROM attendance
                WHERE student_id=%s
                ORDER BY attendance_date DESC
                LIMIT 100
                """,
                (student_id,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return render_template("student/attendance/history.html", rows=rows)

