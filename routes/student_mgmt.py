from __future__ import annotations

from flask import Blueprint, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash
from datetime import datetime
import re

from utils.db import fetch_one, execute
from utils.auth import login_required

bp_student_mgmt = Blueprint("bp_student_mgmt", __name__)


def _is_admin() -> bool:
    return session.get("role") == "admin"


# -----------------------------
# Helpers
# -----------------------------

def _require_admin():
    return _is_admin()



def _safe_date(value: str):
    value = (value or "").strip()
    if not value:
        return None
    # expected: YYYY-MM-DD
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return "__invalid__"


def _slug_name(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"\s+", "_", value)
    # keep letters/numbers/underscore
    value = re.sub(r"[^A-Za-z0-9_@-]", "", value)
    return value


def _generate_student_username(full_name: str, dob: str) -> str:
    name = _slug_name(full_name)
    name = name.strip("_")
    dob_part = (dob or "").strip()
    # normalize dob to YYYY-MM-DD
    dt = _safe_date(dob_part)
    if dt in (None, "__invalid__"):
        return ""
    dob_norm = dt.isoformat()
    return f"{name}_{dob_norm}"


def _generate_student_password(full_name: str) -> str:
    name = _slug_name(full_name)
    name = name.replace("_", "")
    name = name[:30]
    return f"{name}@777"


def _validate_required(form: dict, fields: list[str]) -> list[str]:
    missing = []
    for f in fields:
        if not (form.get(f) or "").strip():
            missing.append(f)
    return missing


def _validate_student_create(payload: dict) -> tuple[bool, list[str]]:
    errors: list[str] = []

    required = [
        "roll_number",
        "full_name",
        "date_of_birth",
        "gender",
        "class",
        "section",
        "parent_name",
        "parent_email",
        "parent_phone",
        "address",
        "admission_date",
    ]
    missing = _validate_required(payload, required)
    if missing:
        errors.append("Please fill all required fields.")

    # invalid dates
    dob = _safe_date(payload.get("date_of_birth"))
    ad = _safe_date(payload.get("admission_date"))
    if dob == "__invalid__" or ad == "__invalid__":
        errors.append("Invalid date format. Use YYYY-MM-DD.")

    # basic email/phone checks
    email = (payload.get("parent_email") or "").strip()
    if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        errors.append("Parent email is not valid.")

    phone = (payload.get("parent_phone") or "").strip()
    if phone and not re.match(r"^[0-9+\-\s]{6,20}$", phone):
        errors.append("Parent phone is not valid.")

    # duplicates (roll_number, parent_email, parent_phone)
    if payload.get("roll_number"):
        r1 = fetch_one("SELECT id FROM students WHERE roll_number=%s", (payload["roll_number"],))
        if r1:
            errors.append("Roll Number already exists.")

    if payload.get("parent_email"):
        r2 = fetch_one(
            "SELECT id FROM students WHERE parent_email=%s",
            (payload["parent_email"],),
        )
        if r2:
            errors.append("Parent Email already exists.")

    if payload.get("parent_phone"):
        r3 = fetch_one(
            "SELECT id FROM students WHERE parent_phone=%s",
            (payload["parent_phone"],),
        )
        if r3:
            errors.append("Parent Phone already exists.")

    return (len(errors) == 0), errors


def _validate_student_update(payload: dict, student_id: int) -> tuple[bool, list[str]]:
    # same as create but allow same row conflicts
    errors: list[str] = []

    required = [
        "roll_number",
        "full_name",
        "date_of_birth",
        "gender",
        "class",
        "section",
        "parent_name",
        "parent_email",
        "parent_phone",
        "address",
        "admission_date",
    ]
    missing = _validate_required(payload, required)
    if missing:
        errors.append("Please fill all required fields.")

    dob = _safe_date(payload.get("date_of_birth"))
    ad = _safe_date(payload.get("admission_date"))
    if dob == "__invalid__" or ad == "__invalid__":
        errors.append("Invalid date format. Use YYYY-MM-DD.")

    email = (payload.get("parent_email") or "").strip()
    if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        errors.append("Parent email is not valid.")

    phone = (payload.get("parent_phone") or "").strip()
    if phone and not re.match(r"^[0-9+\-\s]{6,20}$", phone):
        errors.append("Parent phone is not valid.")

    # duplicates excluding current student
    if payload.get("roll_number"):
        row = fetch_one(
            "SELECT id FROM students WHERE roll_number=%s AND id<>%s",
            (payload["roll_number"], student_id),
        )
        if row:
            errors.append("Roll Number already exists.")

    if payload.get("parent_email"):
        row = fetch_one(
            "SELECT id FROM students WHERE parent_email=%s AND id<>%s",
            (payload["parent_email"], student_id),
        )
        if row:
            errors.append("Parent Email already exists.")

    if payload.get("parent_phone"):
        row = fetch_one(
            "SELECT id FROM students WHERE parent_phone=%s AND id<>%s",
            (payload["parent_phone"], student_id),
        )
        if row:
            errors.append("Parent Phone already exists.")

    return (len(errors) == 0), errors


def _access_denied():
    return render_template("errors/access_denied.html"), 403


# -----------------------------
# Routes: List

# -----------------------------

@bp_student_mgmt.route("/admin/students", methods=["GET"])
@login_required
def list_students():
    if not _require_admin():
        return _access_denied()

    # search
    q = (request.args.get("q") or "").strip()

    name = (request.args.get("name") or "").strip()
    roll_number = (request.args.get("roll_number") or "").strip()
    class_filter = (request.args.get("class") or "").strip()
    section_filter = (request.args.get("section") or "").strip()

    gender_filter = (request.args.get("gender") or "").strip()

    # pagination
    try:
        page = int(request.args.get("page") or 1)
    except Exception:
        page = 1
    page = max(1, page)
    per_page = 10
    offset = (page - 1) * per_page

    where = ["1=1"]
    params: list[object] = []

    # live search (name/roll_number/class/section)
    if q:
        where.append("(full_name LIKE %s OR roll_number LIKE %s OR class LIKE %s OR section LIKE %s)")
        like = f"%{q}%"
        params.extend([like, like, like, like])
    else:
        if name:
            where.append("full_name LIKE %s")
            params.append(f"%{name}%")
        if roll_number:
            where.append("roll_number LIKE %s")
            params.append(f"%{roll_number}%")
        if class_filter:
            where.append("class=%s")
            params.append(class_filter)
        if section_filter:
            where.append("section=%s")
            params.append(section_filter)

    if gender_filter:
        where.append("gender=%s")
        params.append(gender_filter)

    where_sql = " AND ".join(where)

    # total count
    total_row = fetch_one(f"SELECT COUNT(*) AS cnt FROM students WHERE {where_sql}", tuple(params))
    total_cnt = int(total_row["cnt"] if total_row and total_row.get("cnt") is not None else 0)
    total_pages = max(1, (total_cnt + per_page - 1) // per_page)

    page = min(page, total_pages)

    rows = []
    with_params = tuple(params) + (per_page, offset)
    data = fetch_one("SELECT 1")

    # fetch page data
    conn_rows = []
    from utils.db import get_connection
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, roll_number, username, full_name, date_of_birth, gender, class, section, parent_name, parent_email, parent_phone, admission_date
                FROM students
                WHERE {where_sql}
                ORDER BY id DESC
                LIMIT %s OFFSET %s
                """,
                with_params,
            )
            conn_rows = cur.fetchall()
    finally:
        conn.close()

    rows = conn_rows or []

    # distinct values for filters
    def distinct_col(col: str):
        # safe whitelist columns
        allowed = {"class", "section", "gender"}
        if col not in allowed:
            return []
        r = fetch_one(f"SELECT 1")
        conn2 = get_connection()
        try:
            with conn2.cursor() as cur:
                cur.execute(f"SELECT DISTINCT {col} AS v FROM students ORDER BY {col}")
                out = cur.fetchall()
        finally:
            conn2.close()
        return [x["v"] for x in out if x.get("v")]

    classes = distinct_col("class")
    sections = distinct_col("section")
    genders = distinct_col("gender")

    return render_template(
        "admin/students/list.html",
        students=rows,
        page=page,
        total_pages=total_pages,
        total_cnt=total_cnt,
        filters={
            "q": q,
            "name": name,
            "roll_number": roll_number,
            "class": class_filter,
            "section": section_filter,
            "gender": gender_filter,
        },
        classes=classes,
        sections=sections,
        genders=genders,
    )


# -----------------------------
# Routes: Add
# -----------------------------

@bp_student_mgmt.route("/admin/students/add", methods=["GET", "POST"])
@login_required
def add_student():
    if not _require_admin():
        return _access_denied()

    if request.method == "POST":
        form = request.form
        payload = {
            "roll_number": (form.get("roll_number") or "").strip(),
            "full_name": (form.get("full_name") or "").strip(),
            "date_of_birth": (form.get("date_of_birth") or "").strip(),
            "gender": (form.get("gender") or "").strip(),
            "class": (form.get("class") or "").strip(),
            "section": (form.get("section") or "").strip(),
            "parent_name": (form.get("parent_name") or "").strip(),
            "parent_email": (form.get("parent_email") or "").strip(),
            "parent_phone": (form.get("parent_phone") or "").strip(),
            "address": (form.get("address") or "").strip(),
            "admission_date": (form.get("admission_date") or "").strip(),
        }

        ok, errors = _validate_student_create(payload)
        generated_username = _generate_student_username(payload.get("full_name"), payload.get("date_of_birth"))
        generated_password = _generate_student_password(payload.get("full_name"))

        if not ok:
            return render_template(
                "admin/students/add.html",
                errors=errors,
                generated_username=generated_username,
                generated_password=generated_password,
                form=payload,
            )

        # Hash password
        password_hash = generate_password_hash(generated_password)

        execute(
            """
            INSERT INTO students (
              roll_number, username, password, full_name, date_of_birth, gender, class, section,
              parent_name, parent_email, parent_phone, address, admission_date
            ) VALUES (
              %s,%s,%s,%s,%s,%s,%s,%s,
              %s,%s,%s,%s,%s
            )
            """,
            (
                payload["roll_number"],
                generated_username,
                password_hash,
                payload["full_name"],
                payload["date_of_birth"],
                payload["gender"],
                payload["class"],
                payload["section"],
                payload["parent_name"],
                payload["parent_email"],
                payload["parent_phone"],
                payload["address"],
                payload["admission_date"],
            ),
        )

        return render_template(
            "admin/students/add.html",
            success=True,
            success_message="Student added successfully.",
            generated_username=generated_username,
            generated_password=generated_password,
        )

    return render_template(
        "admin/students/add.html",
        errors=None,
        success=False,
        form={},
        generated_username="",
        generated_password="",
    )


# -----------------------------
# Routes: View
# -----------------------------

@bp_student_mgmt.route("/admin/students/<int:student_id>", methods=["GET"])
@login_required
def view_student(student_id: int):
    if not _require_admin():
        return _access_denied()

    row = fetch_one(
        """
        SELECT id, roll_number, username, full_name, date_of_birth, gender, class, section,
               parent_name, parent_email, parent_phone, address, admission_date, created_at, updated_at
        FROM students WHERE id=%s
        """,
        (student_id,),
    )

    if not row:
        return redirect(url_for("bp_student_mgmt.list_students"))

    return render_template("admin/students/view.html", student=row)


# -----------------------------
# Routes: Edit
# -----------------------------

@bp_student_mgmt.route("/admin/students/<int:student_id>/edit", methods=["GET", "POST"])
@login_required
def edit_student(student_id: int):
    if not _require_admin():
        return _access_denied()

    row = fetch_one("SELECT * FROM students WHERE id=%s", (student_id,))
    if not row:
        return redirect(url_for("bp_student_mgmt.list_students"))

    if request.method == "POST":
        form = request.form
        payload = {
            "roll_number": (form.get("roll_number") or "").strip(),
            "full_name": (form.get("full_name") or "").strip(),
            "date_of_birth": (form.get("date_of_birth") or "").strip(),
            "gender": (form.get("gender") or "").strip(),
            "class": (form.get("class") or "").strip(),
            "section": (form.get("section") or "").strip(),
            "parent_name": (form.get("parent_name") or "").strip(),
            "parent_email": (form.get("parent_email") or "").strip(),
            "parent_phone": (form.get("parent_phone") or "").strip(),
            "address": (form.get("address") or "").strip(),
            "admission_date": (form.get("admission_date") or "").strip(),
        }

        ok, errors = _validate_student_update(payload, student_id)

        if not ok:
            row_for_form = dict(row)
            row_for_form.update(payload)
            return render_template("admin/students/edit.html", student=row_for_form, errors=errors)

        execute(
            """
            UPDATE students
            SET roll_number=%s, full_name=%s, date_of_birth=%s, gender=%s, class=%s, section=%s,
                parent_name=%s, parent_email=%s, parent_phone=%s, address=%s, admission_date=%s,
                updated_at=NOW()
            WHERE id=%s
            """,
            (
                payload["roll_number"],
                payload["full_name"],
                payload["date_of_birth"],
                payload["gender"],
                payload["class"],
                payload["section"],
                payload["parent_name"],
                payload["parent_email"],
                payload["parent_phone"],
                payload["address"],
                payload["admission_date"],
                student_id,
            ),
        )

        return redirect(url_for("bp_student_mgmt.view_student", student_id=student_id))

    return render_template("admin/students/edit.html", student=row, errors=None)


# -----------------------------
# Routes: Delete
# -----------------------------

@bp_student_mgmt.route("/admin/students/<int:student_id>/delete", methods=["POST"])
@login_required
def delete_student(student_id: int):
    if not _require_admin():
        return _access_denied()

    # CSRF not implemented in foundation; rely on same-origin + session role.
    confirm = (request.form.get("confirm") or "").strip()
    if confirm != "YES":
        return redirect(url_for("bp_student_mgmt.view_student", student_id=student_id))

    execute("DELETE FROM students WHERE id=%s", (student_id,))
    return redirect(url_for("bp_student_mgmt.list_students"))

