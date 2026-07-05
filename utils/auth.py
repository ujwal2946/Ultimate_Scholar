from functools import wraps

from flask import session, redirect, url_for, request


def login_required(view_fn):
    @wraps(view_fn)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("bp_main.get_started"))
        return view_fn(*args, **kwargs)

    return wrapper


def role_required(role: str):
    def decorator(view_fn):
        @wraps(view_fn)
        def wrapper(*args, **kwargs):
            user = session.get("user")
            if not user:
                return redirect(url_for("bp_main.get_started"))
            if session.get("role") != role:
                # If they hit wrong dashboard, send them to role selection
                return redirect(url_for("bp_main.get_started"))
            return view_fn(*args, **kwargs)

        return wrapper

    return decorator

