from datetime import date, datetime, timedelta


from flask import Blueprint, flash, render_template, request, redirect, url_for, session

from utils.auth import login_required, role_required
from utils.db import execute, fetch_one

from utils.attendance_email import record_and_send_absence_notification


bp_attendance_admin = Blueprint("bp_attendance_admin", __name__)


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


@bp_attendance_admin.route("/dashboard", methods=["GET"])
@login_required
@role_required("admin")
def dashboard():
    today = _today()

    present = fetch_one(
        "SELECT COUNT(*) AS cnt FROM attendance WHERE attendance_date=%s AND status=%s",
        (today, "Present"),
    )
    absent = fetch_one(
        "SELECT COUNT(*) AS cnt FROM attendance WHERE attendance_date=%s AND status=%s",
        (today, "Absent"),
    )
    late = fetch_one(
        "SELECT COUNT(*) AS cnt FROM attendance WHERE attendance_date=%s AND status=%s",
        (today, "Late"),
    )

    present_today = int(present["cnt"] if present else 0)
    absent_today = int(absent["cnt"] if absent else 0)
    late_today = int(late["cnt"] if late else 0)

    total_today = present_today + absent_today + late_today
    attendance_percentage = round((present_today / total_today) * 100, 2) if total_today else 0

    absentees = []
    from utils.db import get_connection

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT a.id, a.student_id, s.roll_number, s.full_name, s.class, s.section, a.status, a.attendance_date
                FROM attendance a
                JOIN students s ON s.id=a.student_id
                WHERE a.attendance_date=%s AND a.status=%s
                ORDER BY s.full_name ASC
                """,
                (today, "Absent"),
            )
            absentees = cur.fetchall()
    finally:
        conn.close()

    return render_template(
        "admin/attendance/dashboard.html",
        present_today=present_today,
        absent_today=absent_today,
        late_today=late_today,
        attendance_percentage=attendance_percentage,
        today=today,
        absentees=absentees,
    )


@bp_attendance_admin.route("/list", methods=["GET"])
@login_required
@role_required("admin")
def list_attendance():
    q = (request.args.get("q") or "").strip()
    status = (request.args.get("status") or "").strip()
    class_filter = (request.args.get("class") or "").strip()
    section_filter = (request.args.get("section") or "").strip()
    roll_number = (request.args.get("roll_number") or "").strip()

    # Basic validation/normalization for filter inputs
    if status and status not in ("Present", "Absent", "Late"):
        status = ""

    date_from = _parse_date(request.args.get("date") or "")
    month = (request.args.get("month") or "").strip()  # YYYY-MM
    if month and month.strip() and len(month) != 7:
        month = ""

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

    if roll_number:
        where.append("s.roll_number LIKE %s")
        params.append(f"%{roll_number}%")

    if class_filter:
        where.append("s.class=%s")
        params.append(class_filter)

    if section_filter:
        where.append("s.section=%s")
        params.append(section_filter)

    if status:
        where.append("a.status=%s")
        params.append(status)

    if date_from:
        where.append("a.attendance_date=%s")
        params.append(date_from)

    if month:
        where.append("DATE_FORMAT(a.attendance_date, '%Y-%m')=%s")
        params.append(month)

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
                       a.attendance_date, a.status, a.marked_by, a.created_at
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
        "admin/attendance/list.html",
        rows=rows,
        page=page,
        total_pages=total_pages,
        total_cnt=total_cnt,
        filters={
            "q": q,
            "status": status,
            "class": class_filter,
            "section": section_filter,
            "roll_number": roll_number,
            "date": request.args.get("date") or "",
            "month": month,
        },
    )


@bp_attendance_admin.route("/mark", methods=["GET", "POST"])
@login_required
@role_required("admin")
def mark_attendance():
    message = None
    from utils.db import get_connection

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT class FROM students ORDER BY class")
            classes = [row["class"] for row in cur.fetchall()]
    finally:
        conn.close()

    selected_class = (request.values.get("class") or "").strip()
    attendance_date = _parse_date(request.values.get("attendance_date") or "") or _today()
    students = []

    if request.method == "POST":
        if selected_class not in classes:
            message = "Please select a valid class."
        else:
            conn = get_connection()
            absent_notifications = []
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT s.id, s.roll_number, s.full_name, s.class, s.section,
                               s.parent_email, a.id AS attendance_id, a.status AS attendance_status
                        FROM students s
                        LEFT JOIN attendance a
                          ON a.student_id=s.id AND a.attendance_date=%s
                        WHERE s.class=%s
                        ORDER BY s.section, s.roll_number, s.full_name
                        """,
                        (attendance_date, selected_class),
                    )
                    students = cur.fetchall()

                    present_ids = set()
                    for value in request.form.getlist("present_student_ids"):
                        try:
                            present_ids.add(int(value))
                        except ValueError:
                            continue

                    for student in students:
                        status = "Present" if student["id"] in present_ids else "Absent"
                        previous_status = student["attendance_status"]
                        if student["attendance_id"]:
                            cur.execute(
                                """
                                UPDATE attendance
                                SET status=%s, marked_by=%s, updated_at=NOW()
                                WHERE id=%s
                                """,
                                (status, session.get("user"), student["attendance_id"]),
                            )
                            attendance_id = student["attendance_id"]
                        else:
                            cur.execute(
                                """
                                INSERT INTO attendance (student_id, attendance_date, status, marked_by)
                                VALUES (%s, %s, %s, %s)
                                """,
                                (student["id"], attendance_date, status, session.get("user")),
                            )
                            attendance_id = cur.lastrowid

                        if status == "Absent" and previous_status != "Absent":
                            absent_notifications.append((student["id"], attendance_id))

                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

            for student_id, attendance_id in absent_notifications:
                sent, notification_message = record_and_send_absence_notification(
                    student_id=student_id,
                    attendance_id=attendance_id,
                    attendance_date=attendance_date,
                    status="Absent",
                )
                flash(notification_message, "success" if sent else "warning")

            flash(f"Attendance saved for {len(students)} students.", "success")
            return redirect(
                url_for(
                    "bp_attendance_admin.mark_attendance",
                    **{"class": selected_class, "attendance_date": attendance_date.isoformat()},
                )
            )

    if selected_class in classes:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT s.id, s.roll_number, s.full_name, s.class, s.section,
                           a.status AS attendance_status
                    FROM students s
                    LEFT JOIN attendance a
                      ON a.student_id=s.id AND a.attendance_date=%s
                    WHERE s.class=%s
                    ORDER BY s.section, s.roll_number, s.full_name
                    """,
                    (attendance_date, selected_class),
                )
                students = cur.fetchall()
        finally:
            conn.close()

    return render_template(
        "admin/attendance/mark.html",
        students=students,
        classes=classes,
        selected_class=selected_class,
        attendance_date=attendance_date,
        today=_today(),
        message=message,
    )


@bp_attendance_admin.route("/delete/<int:attendance_id>", methods=["POST"])
@login_required
@role_required("admin")
def delete_attendance(attendance_id: int):
    execute("DELETE FROM attendance WHERE id=%s", (attendance_id,))
    return redirect(url_for("bp_attendance_admin.list_attendance"))


@bp_attendance_admin.route("/monthly", methods=["GET"])
@login_required
@role_required("admin")
def monthly_attendance():
    month = (request.args.get("month") or "").strip() or datetime.today().strftime("%Y-%m")

    # Month filter (robust): avoid DATE_FORMAT with '%Y-%m' because
    # it can break depending on PyMySQL mogrify/% escaping and attendance_date type.
    # Use a safe date range: [month-01, next_month-01)
    try:
        month_start = datetime.strptime(month + '-01', '%Y-%m-%d').date()
    except Exception:
        month_start = None

    if month_start is None:
        # invalid month format => return zeros
        present_cnt = absent_cnt = late_cnt = 0
        total = 0
        attendance_percentage = 0
        return render_template(
            'admin/attendance/monthly.html',
            month=month,
            present_cnt=present_cnt,
            absent_cnt=absent_cnt,
            late_cnt=late_cnt,
            attendance_percentage=attendance_percentage,
        )

    next_month = (datetime(month_start.year, month_start.month, 1).replace(day=28) + timedelta(days=4)).date().replace(day=1)
    month_end = next_month  # first day of next month

    present = fetch_one(
        """
        SELECT COUNT(*) AS cnt
        FROM attendance
        WHERE attendance_date >= %s AND attendance_date < %s AND status=%s
        """,
        (month_start, month_end, 'Present'),
    )
    absent = fetch_one(
        """
        SELECT COUNT(*) AS cnt
        FROM attendance
        WHERE attendance_date >= %s AND attendance_date < %s AND status=%s
        """,
        (month_start, month_end, 'Absent'),
    )
    late = fetch_one(
        """
        SELECT COUNT(*) AS cnt
        FROM attendance
        WHERE attendance_date >= %s AND attendance_date < %s AND status=%s
        """,
        (month_start, month_end, 'Late'),
    )



    present_cnt = int(present["cnt"] if present else 0)
    absent_cnt = int(absent["cnt"] if absent else 0)
    late_cnt = int(late["cnt"] if late else 0)

    total = present_cnt + absent_cnt + late_cnt
    attendance_percentage = round((present_cnt / total) * 100, 2) if total else 0

    return render_template(
        "admin/attendance/monthly.html",
        month=month,
        present_cnt=present_cnt,
        absent_cnt=absent_cnt,
        late_cnt=late_cnt,
        attendance_percentage=attendance_percentage,
    )
