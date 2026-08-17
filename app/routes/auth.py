"""Authentication routes for registration, login, and logout."""

import os

from flask import flash, redirect, render_template, request, session, url_for

from app.services import portfolio_service as service


def register_routes(app):
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    @app.context_processor
    def inject_user():
        user_id = session.get("user_id")
        return {"logged_in_user": service.fetch_user(user_id) if user_id else None}

    @app.route("/")
    def home():
        return render_template("home.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            if not username or not email or not password:
                flash("All fields are required.", "danger")
            elif len(password) < 8:
                flash("Password must be at least 8 characters long.", "danger")
            else:
                ok, message = service.register_user(username, email, password)
                flash(message, "success" if ok else "danger")
                if ok:
                    return redirect(url_for("login"))
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = service.authenticate_user(email, password)
            if not user:
                flash("Invalid email or password.", "danger")
            else:
                session.clear()
                session["user_id"] = user["user_id"]
                flash("Welcome back.", "success")
                return redirect(url_for("dashboard_page"))
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        flash("You have been logged out.", "info")
        return redirect(url_for("home"))
