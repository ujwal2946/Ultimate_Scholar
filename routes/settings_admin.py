from flask import Blueprint, render_template, request, session, redirect, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from utils.auth import login_required, role_required
from utils.db import fetch_one, execute

bp_settings_admin = Blueprint("bp_settings_admin", __name__)


def _require_admin():
    return session.get("role") == "admin"


@bp_settings_admin.route("/dashboard", methods=["GET"])
@login_required
@role_required("admin")
def dashboard():
    # Placeholder settings landing
    return render_template("admin/settings/dashboard.html")


@bp_settings_admin.route("/change-password", methods=["POST"])
@login_required
@role_required("admin")
def change_password():
    # For now, admin users table only stores username/password.
    current_password = request.form.get("current_password") or ""
    new_password = request.form.get("new_password") or ""

    if not current_password or not new_password:
        return redirect(url_for("bp_settings_admin.dashboard"))

    row = fetch_one("SELECT id, password FROM admins WHERE id=%s", (session.get("user"),))
    if not row or not check_password_hash(row.get("password"), current_password):
        return redirect(url_for("bp_settings_admin.dashboard"))

    new_hash = generate_password_hash(new_password)
    execute("UPDATE admins SET password=%s WHERE id=%s", (new_hash, session.get("user")))
    return redirect(url_for("bp_settings_admin.dashboard"))

