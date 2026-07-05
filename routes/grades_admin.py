from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, session
from utils.auth import login_required, role_required
from utils.db import execute, fetch_one

bp_grades_admin = Blueprint("bp_grades_admin", __name__)


def _access_denied():
    return render_template("errors/access_denied.html"), 403


def _require_admin():
    return session.get("role") == "admin"


def _parse_int(v, default=None):
    try:
        v = (v or "").strip()
        if not v:
            return default
        return int(v)
    except Exception:
        return default


def _compute_grade(marks: int) -> str:
    # Default grading policy (can be changed later):
    # 90-100: A, 80-89: B, 70-79: C, 60-69: D, <60: F
    if marks >= 90:
        return "A"
    if marks >= 80:
        return "B"
    if marks >= 70:
        return "C"
    if marks >= 60:
        return "D"
    return "F"


@bp_grades_admin.route("/dashboard", methods=["GET"])
@login_required
@role_required("admin")
def dashboard():
    # Admin dashboard aggregates
    avg_grade_row = fetch_one(
        """
        SELECT AVG(marks) AS avg_marks
        FROM grades
        """
    )
    avg_marks = float(avg_grade_row["avg_marks"] or 0) if avg_grade_row else 0.0

    # Top/Recent
    # Top performer by overall percentage: compute avg marks per student normalized by count.
    top_row = fetch_one(
        """
        SELECT g.student_id, s.full_name, s.roll_number, AVG(g.marks) AS avg_marks
        FROM grades g
        JOIN students s ON s.id=g.student_id
        GROUP BY g.student_id
        ORDER BY avg_marks DESC
        LIMIT 1
        """
    )

    top_student = top_row

    recent_rows = []
    from utils.db import get_connection

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT g.id, g.student_id, s.roll_number, s.full_name, g.subject, g.marks, g.grade, g.semester, g.created_at
                FROM grades g
                JOIN students s ON s.id=g.student_id
                ORDER BY g.created_at DESC
                LIMIT 10
                """
            )
            recent_rows = cur.fetchall()
    finally:
        conn.close()

    return render_template(
        "admin/grades/dashboard.html",
        avg_marks=round(avg_marks, 2),
        top_student=top_student,
        recent_rows=recent_rows,
    )


@bp_grades_admin.route("/list", methods=["GET"])
@login_required
@role_required("admin")
def list_grades():
    q_student = (request.args.get("student") or "").strip()
    q_subject = (request.args.get("subject") or "").strip()
    q_semester = (request.args.get("semester") or "").strip()

    try:
        page = int(request.args.get("page") or 1)
    except Exception:
        page = 1
    page = max(1, page)
    per_page = 10
    offset = (page - 1) * per_page

    where = ["1=1"]
    params = []

    if q_student:
        where.append("(s.full_name LIKE %s OR s.roll_number LIKE %s)")
        like = f"%{q_student}%"
        params.extend([like, like])

    if q_subject:
        where.append("g.subject LIKE %s")
        params.append(f"%{q_subject}%")

    if q_semester:
        where.append("g.semester LIKE %s")
        params.append(f"%{q_semester}%")

    where_sql = " AND ".join(where)

    total_row = fetch_one(
        f"""
        SELECT COUNT(*) AS cnt
        FROM grades g
        JOIN students s ON s.id=g.student_id
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
                SELECT g.id, g.student_id, s.roll_number, s.full_name, g.subject, g.marks, g.grade, g.semester, g.created_at
                FROM grades g
                JOIN students s ON s.id=g.student_id
                WHERE {where_sql}
                ORDER BY g.created_at DESC
                LIMIT %s OFFSET %s
                """,
                tuple(params) + (per_page, offset),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return render_template(
        "admin/grades/list.html",
        rows=rows,
        page=page,
        total_pages=total_pages,
        total_cnt=total_cnt,
        filters={"student": q_student, "subject": q_subject, "semester": q_semester},
    )


@bp_grades_admin.route("/add", methods=["GET", "POST"])
@login_required
@role_required("admin")
def add_grade():
    message = None

    if request.method == "POST":
        student_id = _parse_int(request.form.get("student_id"))
        subject = (request.form.get("subject") or "").strip()
        marks = _parse_int(request.form.get("marks"))
        semester = (request.form.get("semester") or "").strip()

        if not student_id or not subject or marks is None or not semester:
            message = "Please fill all fields."
        else:
            if marks < 0:
                message = "Marks must be >= 0."
            else:
                grade = _compute_grade(marks)
                execute(
                    """
                    INSERT INTO grades (student_id, subject, marks, grade, semester)
                    VALUES (%s,%s,%s,%s,%s)
                    """,
                    (student_id, subject, marks, grade, semester),
                )
                return redirect(url_for("bp_grades_admin.list_grades"))

    from utils.db import get_connection
    conn = get_connection()
    students = []
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, roll_number, full_name FROM students ORDER BY full_name ASC")
            students = cur.fetchall()
    finally:
        conn.close()

    return render_template(
        "admin/grades/form.html",
        mode="add",
        students=students,
        message=message,
        form={},
    )


@bp_grades_admin.route("/<int:grade_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin")
def edit_grade(grade_id: int):
    message = None
    row = fetch_one(
        """
        SELECT g.*,
               s.roll_number, s.full_name
        FROM grades g
        JOIN students s ON s.id=g.student_id
        WHERE g.id=%s
        """,
        (grade_id,),
    )
    if not row:
        return redirect(url_for("bp_grades_admin.list_grades"))

    if request.method == "POST":
        student_id = _parse_int(request.form.get("student_id"))
        subject = (request.form.get("subject") or "").strip()
        marks = _parse_int(request.form.get("marks"))
        semester = (request.form.get("semester") or "").strip()

        if not student_id or not subject or marks is None or not semester:
            message = "Please fill all fields."
        else:
            if marks < 0:
                message = "Marks must be >= 0."
            else:
                grade = _compute_grade(marks)
                execute(
                    """
                    UPDATE grades
                    SET student_id=%s, subject=%s, marks=%s, grade=%s, semester=%s, created_at=created_at
                    WHERE id=%s
                    """,
                    (student_id, subject, marks, grade, semester, grade_id),
                )
                return redirect(url_for("bp_grades_admin.list_grades"))

    from utils.db import get_connection
    conn = get_connection()
    students = []
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, roll_number, full_name FROM students ORDER BY full_name ASC")
            students = cur.fetchall()
    finally:
        conn.close()

    form = {
        "student_id": row.get("student_id"),
        "subject": row.get("subject"),
        "marks": row.get("marks"),
        "semester": row.get("semester"),
    }

    return render_template(
        "admin/grades/form.html",
        mode="edit",
        students=students,
        message=message,
        form=form,
    )


@bp_grades_admin.route("/<int:grade_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_grade(grade_id: int):
    execute("DELETE FROM grades WHERE id=%s", (grade_id,))
    return redirect(url_for("bp_grades_admin.list_grades"))

