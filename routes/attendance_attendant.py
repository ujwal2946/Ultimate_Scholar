from datetime import date, datetime

from flask import Blueprint, render_template, request, redirect, url_for, session

from utils.auth import login_required, role_required
from utils.db import execute, fetch_one
from utils.attendance_email import record_and_send_absence_notification


bp_attendance_attendant = Blueprint("bp_attendance_attendant", __name__)


def _today():
    return date.today()


def _parse_date(s: str):
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


@bp_attendance_attendant.route("/dashboard", methods=["GET"])
@login_required
@role_required("attendant")
def dashboard():
    return render_template("attendant/attendance/dashboard.html", today=_today())


@bp_attendance_attendant.route("/quick", methods=["GET", "POST"])
@login_required
@role_required("attendant")
def quick_entry():
    msg = None
    if request.method == "POST":
        attendance_date = _parse_date(request.form.get("attendance_date")) or _today()
        student_id = int((request.form.get("student_id") or "0").strip() or 0)
        status = (request.form.get("status") or "").strip()

        if status not in ("Present", "Absent", "Late"):
            msg = "Invalid status"
        else:
            existing = fetch_one(
                "SELECT id FROM attendance WHERE student_id=%s AND attendance_date=%s",
                (student_id, attendance_date),
            )
            if existing:
                execute(
                    """
                    UPDATE attendance
                    SET status=%s, marked_by=%s, updated_at=NOW()
                    WHERE id=%s
                    """,
                    (status, session.get("user"), existing["id"]),
                )
                attendance_id = existing["id"]
            else:
                execute(
                    """
                    INSERT INTO attendance (student_id, attendance_date, status, marked_by)
                    VALUES (%s,%s,%s,%s)
                    """,
                    (student_id, attendance_date, status, session.get("user")),
                )
                row = fetch_one(
                    "SELECT id FROM attendance WHERE student_id=%s AND attendance_date=%s",
                    (student_id, attendance_date),
                )
                attendance_id = row["id"] if row else None

            if status == "Absent" and attendance_id:
                record_and_send_absence_notification(
                    student_id=student_id,
                    attendance_id=attendance_id,
                    attendance_date=attendance_date,
                    status=status,
                )

            return redirect(url_for("bp_attendance_attendant.history"))

    from utils.db import get_connection

    conn = get_connection()
    students = []
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, roll_number, full_name, class, section FROM students ORDER BY full_name ASC")
            students = cur.fetchall()
    finally:
        conn.close()

    return render_template(
        "attendant/attendance/quick.html",
        students=students,
        today=_today(),
        message=msg,
    )


@bp_attendance_attendant.route("/history", methods=["GET"])
@login_required
@role_required("attendant")
def history():
    # Recent attendance + search/pagination
    q = (request.args.get("q") or "").strip()
    status = (request.args.get("status") or "").strip()

    try:
        page = int(request.args.get("page") or 1)
    except Exception:
        page = 1
    page = max(1, page)
    per_page = 10
    offset = (page - 1) * per_page

    where = ["1=1"]
    params = []
    if q:
        where.append("s.full_name LIKE %s")
        params.append(f"%{q}%")
    if status:
        where.append("a.status=%s")
        params.append(status)

    where_sql = " AND ".join(where)

    total_row = fetch_one(
        f"""
        SELECT COUNT(*) AS cnt
        FROM attendance a
        JOIN students s ON s.id=a.student_id
        WHERE {where_sql}
        """,
        tuple(params),
    )
    total_cnt = int(total_row["cnt"] if total_row and total_row.get("cnt") is not None else 0)
    total_pages = max(1, (total_cnt + per_page - 1) // per_page)
    page = min(page, total_pages)

    from utils.db import get_connection

    conn = get_connection()
    rows = []
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT a.id, a.student_id, s.roll_number, s.full_name, s.class, s.section,
                       a.attendance_date, a.status, a.marked_by
                FROM attendance a
                JOIN students s ON s.id=a.student_id
                WHERE {where_sql}
                ORDER BY a.attendance_date DESC, s.full_name ASC
                LIMIT %s OFFSET %s
                """,
                tuple(params) + (per_page, offset),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return render_template(
        "attendant/attendance/history.html",
        rows=rows,
        page=page,
        total_pages=total_pages,
        total_cnt=total_cnt,
        filters={"q": q, "status": status},
    )


@bp_attendance_attendant.route("/update/<int:attendance_id>", methods=["POST"])
@login_required
@role_required("attendant")
def update(attendance_id: int):
    status = (request.form.get("status") or "").strip()
    if status not in ("Present", "Absent", "Late"):
        return redirect(url_for("bp_attendance_attendant.history"))

    attendance = fetch_one("SELECT id, student_id, attendance_date FROM attendance WHERE id=%s", (attendance_id,))
    execute(
        """
        UPDATE attendance
        SET status=%s, marked_by=%s, updated_at=NOW()
        WHERE id=%s
        """,
        (status, session.get("user"), attendance_id),
    )

    # Only send email when marked ABSENT.
    if status == "Absent" and attendance:
        record_and_send_absence_notification(
            student_id=attendance["student_id"],
            attendance_id=attendance_id,
            attendance_date=attendance["attendance_date"],
            status=status,
        )

    return redirect(url_for("bp_attendance_attendant.history"))


@bp_attendance_attendant.route("/delete/<int:attendance_id>", methods=["POST"])
@login_required
@role_required("attendant")
def delete(attendance_id: int):
    execute("DELETE FROM attendance WHERE id=%s", (attendance_id,))
    return redirect(url_for("bp_attendance_attendant.history"))

