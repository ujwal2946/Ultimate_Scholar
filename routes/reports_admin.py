from datetime import date, datetime
import csv
import io

from flask import Blueprint, render_template, request, redirect, url_for, send_file

from utils.auth import login_required, role_required
from utils.db import fetch_one

bp_reports_admin = Blueprint("bp_reports_admin", __name__)


def _parse_date(s: str):
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def _today():
    return date.today()


def _default_month():
    return datetime.today().strftime("%Y-%m")


@bp_reports_admin.route("/dashboard", methods=["GET"])
@login_required
@role_required("admin")
def dashboard():
    return render_template("admin/reports/dashboard.html")


@bp_reports_admin.route("/attendance", methods=["GET"])
@login_required
@role_required("admin")
def attendance_report():
    month = (request.args.get("month") or "").strip() or _default_month()
    class_filter = (request.args.get("class") or "").strip()
    section_filter = (request.args.get("section") or "").strip()
    status = (request.args.get("status") or "").strip()  # Present/Absent/Late

    where = ["1=1"]
    params = []

    if month:
        where.append("DATE_FORMAT(a.attendance_date, '%Y-%m')=%s")
        params.append(month)

    if class_filter:
        where.append("s.class=%s")
        params.append(class_filter)

    if section_filter:
        where.append("s.section=%s")
        params.append(section_filter)

    if status:
        where.append("a.status=%s")
        params.append(status)

    where_sql = " AND ".join(where)

    rows = []
    from utils.db import get_connection

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT a.id, a.student_id, s.roll_number, s.full_name, s.class, s.section,
                       a.attendance_date, a.status
                FROM attendance a
                JOIN students s ON s.id=a.student_id
                WHERE {where_sql}
                ORDER BY a.attendance_date DESC, s.full_name ASC
                LIMIT 500
                """,
                tuple(params),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    def _count(st: str):
        r = fetch_one(
            f"""
            SELECT COUNT(*) AS cnt
            FROM attendance a
            JOIN students s ON s.id=a.student_id
            WHERE {where_sql} AND a.status=%s
            """,
            tuple(params) + (st,),
        )
        try:
            return int(r["cnt"] if r and r.get("cnt") is not None else 0)
        except (TypeError, ValueError):
            return 0

    present_cnt = _count("Present")
    absent_cnt = _count("Absent")
    late_cnt = _count("Late")

    total_cnt = present_cnt + absent_cnt + late_cnt
    attendance_percentage = round((present_cnt / total_cnt) * 100, 2) if total_cnt else 0

    return render_template(
        "admin/reports/attendance_report.html",
        rows=rows,
        filters={"month": month, "class": class_filter, "section": section_filter, "status": status},
        present_cnt=present_cnt,
        absent_cnt=absent_cnt,
        late_cnt=late_cnt,
        attendance_percentage=attendance_percentage,
    )


@bp_reports_admin.route("/export/csv/attendance", methods=["POST"])
@login_required
@role_required("admin")
def export_attendance_csv():
    month = (request.form.get("month") or "").strip() or _default_month()
    class_filter = (request.form.get("class") or "").strip()
    section_filter = (request.form.get("section") or "").strip()
    status = (request.form.get("status") or "").strip()

    where = ["1=1"]
    params = []

    if month:
        where.append("DATE_FORMAT(a.attendance_date, '%Y-%m')=%s")
        params.append(month)
    if class_filter:
        where.append("s.class=%s")
        params.append(class_filter)
    if section_filter:
        where.append("s.section=%s")
        params.append(section_filter)
    if status:
        where.append("a.status=%s")
        params.append(status)

    where_sql = " AND ".join(where)

    from utils.db import get_connection

    conn = get_connection()
    rows = []
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT a.id, a.student_id, s.roll_number, s.full_name, s.class, s.section,
                       a.attendance_date, a.status
                FROM attendance a
                JOIN students s ON s.id=a.student_id
                WHERE {where_sql}
                ORDER BY a.attendance_date DESC, s.full_name ASC
                """,
                tuple(params),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "attendance_id",
            "student_id",
            "roll_number",
            "full_name",
            "class",
            "section",
            "date",
            "status",
        ]
    )
    for r in rows:
        writer.writerow(
            [
                r.get("id"),
                r.get("student_id"),
                r.get("roll_number"),
                r.get("full_name"),
                r.get("class"),
                r.get("section"),
                r.get("attendance_date"),
                r.get("status"),
            ]
        )

    buf.seek(0)
    filename = f"attendance_report_{month}.csv"
    return send_file(
        io.BytesIO(buf.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename,
    )

