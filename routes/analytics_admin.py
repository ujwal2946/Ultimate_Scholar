from datetime import datetime

from flask import Blueprint, render_template, session

from utils.auth import login_required, role_required
from utils.db import fetch_one

bp_analytics_admin = Blueprint("bp_analytics_admin", __name__)


def _default_month():
    return datetime.today().strftime("%Y-%m")


@bp_analytics_admin.route("/dashboard", methods=["GET"])
@login_required
@role_required("admin")
def dashboard():
    month = (datetime.today().strftime("%Y-%m"))

    def _count(st: str, where_month: str):
        r = fetch_one(
            """
            SELECT COUNT(*) AS cnt
            FROM attendance
            WHERE DATE_FORMAT(attendance_date,'%Y-%m')=%s AND status=%s
            """,
            (where_month, st),
        )
        return int(r["cnt"] if r and r.get("cnt") is not None else 0)

    present_cnt = _count("Present", month)
    absent_cnt = _count("Absent", month)
    late_cnt = _count("Late", month)

    total_cnt = present_cnt + absent_cnt + late_cnt
    attendance_percentage = round((present_cnt / total_cnt) * 100, 2) if total_cnt else 0

    # Grade distribution (A/B/C/D/F)
    grade_dist_rows = []
    from utils.db import get_connection

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT grade, COUNT(*) AS cnt
                FROM grades
                GROUP BY grade
                ORDER BY grade ASC
                """
            )
            grade_dist_rows = cur.fetchall()
    finally:
        conn.close()

    grade_labels = [str(r.get("grade") or "Unassigned") for r in (grade_dist_rows or [])]
    grade_values = [int(r.get("cnt") or 0) for r in (grade_dist_rows or [])]

    # NOTE: This foundation keeps charts simple; refine metrics later.
    return render_template(
        "admin/analytics/dashboard.html",
        month=month,
        present_cnt=present_cnt,
        absent_cnt=absent_cnt,
        late_cnt=late_cnt,
        attendance_percentage=attendance_percentage,
        grade_labels=grade_labels,
        grade_values=grade_values,
    )

