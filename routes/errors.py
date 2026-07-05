from flask import Blueprint, render_template

bp_errors = Blueprint("bp_errors", __name__)


@bp_errors.app_errorhandler(404)
def not_found(e):
    return render_template("errors/404.html"), 404


@bp_errors.app_errorhandler(500)
def internal_error(e):
    return render_template("errors/500.html"), 500

