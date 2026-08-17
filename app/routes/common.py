"""Shared route helpers such as authentication guards and form parsing."""

from functools import wraps

from flask import flash, redirect, session, url_for


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def parse_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
