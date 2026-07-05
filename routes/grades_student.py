from flask import Blueprint, render_template, session, request

from utils.auth import login_required, role_required
from utils.db import fetch_one

bp_grades_student = Blueprint("bp_grades_student", __name__)


def _compute_grade_points(grade: str) -> float:
    # Default GPA mapping for letter grades.
    # A=4, B=3, C=2, D=1, F=0
    g = (grade or "").upper().strip()
    if g == "A":
        return 4.0
    if g == "B":
        return 3.0
    if g == "C":
        return 2.0
    if g == "D":
        return 1.0
    return 0.0


@bp_grades_student.route("/grades", methods=["GET"])
@login_required
@role_required("student")
def dashboard():
    student_id = session.get("user")

    # Subject-wise marks (latest entry per subject+semester OR all entries aggregated?).
    # We'll use average marks per subject across all semesters.
    subject_rows = []
    overall_rows = []

    from utils.db import get_connection

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT g.subject,
                       AVG(g.marks) AS avg_marks,
                       AVG(g.marks) AS overall_avg_marks,
                       COUNT(*) AS cnt
                FROM grades g
                WHERE g.student_id=%s
                GROUP BY g.subject
                ORDER BY g.subject ASC
                """,
                (student_id,),
            )
            subject_rows = cur.fetchall()

            cur.execute(
                """
                SELECT AVG(marks) AS avg_marks,
                       SUM(marks) AS sum_marks,
                       COUNT(*) AS cnt
                FROM grades
                WHERE student_id=%s
                """,
                (student_id,),
            )
            overall_rows = cur.fetchall()

            # Semester-wise chart: avg marks per semester
            cur.execute(
                """
                SELECT semester, AVG(marks) AS avg_marks
                FROM grades
                WHERE student_id=%s
                GROUP BY semester
                ORDER BY semester ASC
                """,
                (student_id,),
            )
            sem_rows = cur.fetchall()

            # Grade history (latest 50)
            cur.execute(
                """
                SELECT g.id, g.subject, g.marks, g.grade, g.semester, g.created_at
                FROM grades g
                WHERE g.student_id=%s
                ORDER BY g.created_at DESC
                LIMIT 50
                """,
                (student_id,),
            )
            history_rows = cur.fetchall()

    finally:
        conn.close()

    overall = overall_rows[0] if overall_rows else None
    cnt = int(overall["cnt"] or 0) if overall else 0
    avg_marks = float(overall["avg_marks"] or 0) if overall else 0.0

    # Percentage assumes marks are out of 100.
    overall_percentage = round((avg_marks / 100.0) * 100.0, 2) if cnt else 0.0

    # GPA: use average of grade points across grade entries
    gpa = 0.0
    if cnt:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT AVG(marks) AS avg_marks
                    FROM grades
                    WHERE student_id=%s
                    """,
                    (student_id,),
                )
        finally:
            conn.close()

        # Better: fetch grade points per entry
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT grade
                    FROM grades
                    WHERE student_id=%s
                    """,
                    (student_id,),
                )
                grades_list = cur.fetchall()
        finally:
            conn.close()

        total_points = 0.0
        for r in grades_list or []:
            total_points += _compute_grade_points(r.get("grade"))
        gpa = round(total_points / cnt, 2) if cnt else 0.0

    # Charts data
    sem_labels = [r.get("semester") for r in (sem_rows or [])]
    sem_values = [float(r.get("avg_marks") or 0) for r in (sem_rows or [])]

    # Performance Graph: semester average marks (computed once server-side)
    perf_labels = sem_labels
    perf_values = sem_values

    return render_template(
        "student/grades/dashboard.html",
        subject_rows=subject_rows,
        overall_percentage=overall_percentage,
        avg_marks=round(avg_marks, 2),
        gpa=gpa,
        sem_labels=sem_labels,
        sem_values=sem_values,
        perf_labels=perf_labels,
        perf_values=perf_values,
        history_rows=history_rows,
    )


