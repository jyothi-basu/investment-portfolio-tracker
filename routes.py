from functools import wraps
import os

from flask import flash, redirect, render_template, request, session, url_for

from ai_chat import ChatServiceError, get_chat_response
import service


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


def build_chat_context(user_id):
    summary = service.calculate_portfolio_summary(user_id)
    holdings = service.calculate_holdings_by_symbol(user_id)

    lines = [
        f"Total investment: Rs. {summary['total_investment']:.2f}",
        f"Current portfolio value: Rs. {summary['current_portfolio_value']:.2f}",
        f"Profit / loss: Rs. {summary['profit_loss']:.2f}",
        f"Total stocks held: {summary['total_stocks_held']}",
        f"Total demat accounts: {summary['total_demat_accounts']}",
    ]

    if holdings:
        lines.append("Current holdings:")
        for item in holdings:
            lines.append(
                f"- {item['stock_symbol']}: quantity {item['quantity']}, "
                f"current price Rs. {item['current_price']:.2f}, "
                f"current value Rs. {item['current_value']:.2f}"
            )
    else:
        lines.append("Current holdings: none.")

    return "\n".join(lines)


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

    @app.route("/dashboard")
    @login_required
    def dashboard_page():
        user_id = session["user_id"]
        return render_template(
            "dashboard.html",
            summary=service.calculate_portfolio_summary(user_id),
            accounts=service.fetch_accounts(user_id),
            holdings=service.calculate_holdings_by_symbol(user_id),
        )

    @app.route("/accounts", methods=["GET", "POST"])
    @login_required
    def accounts_page():
        user_id = session["user_id"]
        editing_account = None
        if request.method == "POST":
            broker_name = request.form.get("broker_name", "").strip()
            account_id = request.form.get("account_id", "").strip()
            if not broker_name:
                flash("Broker name is required.", "danger")
            elif account_id:
                account_pk = parse_int(account_id)
                if account_pk is None:
                    flash("Account not found.", "danger")
                else:
                    ok, message = service.update_account(account_pk, user_id, broker_name)
                    flash(message, "success" if ok else "danger")
                    if ok:
                        return redirect(url_for("accounts_page"))
            else:
                ok, message = service.create_account(user_id, broker_name)
                flash(message, "success" if ok else "danger")
                if ok:
                    return redirect(url_for("accounts_page"))

        edit_id = request.args.get("edit_id")
        if edit_id:
            edit_pk = parse_int(edit_id)
            if edit_pk is None:
                flash("Account not found.", "danger")
                return redirect(url_for("accounts_page"))
            editing_account = service.fetch_account(edit_pk, user_id)
            if not editing_account:
                flash("Account not found.", "danger")
                return redirect(url_for("accounts_page"))

        return render_template(
            "demat_accounts.html",
            accounts=service.fetch_accounts(user_id),
            editing_account=editing_account,
        )

    @app.route("/accounts/delete/<int:account_id>")
    @login_required
    def delete_account(account_id):
        ok, message = service.delete_account(account_id, session["user_id"])
        flash(message, "success" if ok else "danger")
        return redirect(url_for("accounts_page"))

    @app.route("/transactions", methods=["GET", "POST"])
    @login_required
    def transactions_page():
        user_id = session["user_id"]
        editing_transaction = None
        accounts_list = service.fetch_accounts(user_id)
        if request.method == "POST":
            transaction_id = request.form.get("transaction_id", "").strip()
            account_id = request.form.get("account_id", "").strip()
            stock_symbol = request.form.get("stock_symbol", "").strip().upper()
            transaction_type = request.form.get("transaction_type", "").strip().upper()
            quantity = request.form.get("quantity", "").strip()
            price_per_share = request.form.get("price_per_share", "").strip()
            transaction_date = request.form.get("transaction_date", "").strip()

            account_pk = parse_int(account_id)
            tx_pk = parse_int(transaction_id) if transaction_id else None

            if account_pk is None or not stock_symbol or transaction_type not in {"BUY", "SELL"}:
                flash("Please enter valid transaction details.", "danger")
            else:
                try:
                    quantity_value = int(quantity)
                    price_value = float(price_per_share)
                except ValueError:
                    flash("Quantity and price must be valid numbers.", "danger")
                else:
                    if quantity_value <= 0:
                        flash("Quantity must be greater than zero.", "danger")
                    elif price_value <= 0:
                        flash("Price per share must be greater than zero.", "danger")
                    elif not transaction_date:
                        flash("Transaction date is required.", "danger")
                    elif tx_pk is not None:
                        ok, message = service.update_transaction(
                            user_id,
                            tx_pk,
                            account_pk,
                            stock_symbol,
                            transaction_type,
                            quantity_value,
                            price_value,
                            transaction_date,
                        )
                        flash(message, "success" if ok else "danger")
                        if ok:
                            return redirect(url_for("transactions_page"))
                    else:
                        ok, message = service.create_transaction(
                            user_id,
                            account_pk,
                            stock_symbol,
                            transaction_type,
                            quantity_value,
                            price_value,
                            transaction_date,
                        )
                        flash(message, "success" if ok else "danger")
                        if ok:
                            return redirect(url_for("transactions_page"))

        edit_id = request.args.get("edit_id")
        if edit_id:
            edit_pk = parse_int(edit_id)
            if edit_pk is None:
                flash("Transaction not found.", "danger")
                return redirect(url_for("transactions_page"))
            editing_transaction = service.fetch_transaction(edit_pk, user_id)
            if not editing_transaction:
                flash("Transaction not found.", "danger")
                return redirect(url_for("transactions_page"))

        return render_template(
            "transactions.html",
            transactions=service.fetch_transactions(user_id),
            accounts=accounts_list,
            editing_transaction=editing_transaction,
        )

    @app.route("/transactions/delete/<int:transaction_id>")
    @login_required
    def delete_transaction(transaction_id):
        ok, message = service.delete_transaction(transaction_id, session["user_id"])
        flash(message, "success" if ok else "danger")
        return redirect(url_for("transactions_page"))

    @app.route("/prices", methods=["GET", "POST"])
    @login_required
    def prices_page():
        user_id = session["user_id"]
        holdings = service.calculate_holdings_by_symbol(user_id)
        holding_symbols = {item["stock_symbol"] for item in holdings}
        selected_symbol = ""
        entered_price = ""
        if request.method == "POST":
            stock_symbol = request.form.get("stock_symbol", "").strip().upper()
            current_price = request.form.get("current_price", "").strip()
            selected_symbol = stock_symbol
            entered_price = current_price

            if not holdings:
                flash("Add at least one stock transaction before updating prices.", "danger")
            elif not stock_symbol:
                flash("Stock symbol is required.", "danger")
            elif stock_symbol not in holding_symbols:
                flash("You can only update prices for stocks you currently hold.", "danger")
            else:
                try:
                    current_price_value = float(current_price)
                except ValueError:
                    flash("Current price must be a valid number.", "danger")
                else:
                    if current_price_value <= 0:
                        flash("Current price must be greater than zero.", "danger")
                    else:
                        ok, message = service.save_price(user_id, stock_symbol, current_price_value)
                        flash(message, "success" if ok else "danger")
                        if ok:
                            return redirect(url_for("prices_page"))

        return render_template(
            "stock_prices.html",
            holdings=holdings,
            selected_symbol=selected_symbol,
            entered_price=entered_price,
        )

    @app.route("/holdings")
    @login_required
    def holdings_page():
        return render_template("holdings.html", holdings=service.calculate_holdings_by_symbol(session["user_id"]))

    @app.route("/account-summary")
    @login_required
    def account_summary_page():
        user_id = session["user_id"]
        summaries = []
        for account in service.calculate_holdings_by_account(user_id):
            symbols = [s for s in account["symbols"] if s["quantity"] > 0]
            summaries.append(
                {
                    "account_id": account["account_id"],
                    "broker_name": account["broker_name"],
                    "number_of_stocks": len(symbols),
                    "investment_value": account["investment_value"],
                    "current_value": account["current_value"],
                    "profit_loss": account["current_value"] - account["investment_value"],
                }
            )
        return render_template("account_summary.html", summaries=summaries)

    @app.route("/portfolio-summary")
    @login_required
    def portfolio_summary_page():
        return render_template(
            "portfolio_summary.html",
            summary=service.calculate_portfolio_summary(session["user_id"]),
        )

    @app.route("/chat", methods=["GET", "POST"])
    @login_required
    def chat_page():
        user_id = session["user_id"]
        chat_history = session.get("chat_history", [])[-6:]
        user_message = ""
        assistant_reply = ""

        if request.method == "POST":
            user_message = request.form.get("message", "").strip()
            if not user_message:
                flash("Please enter a message.", "danger")
            else:
                try:
                    assistant_reply = get_chat_response(
                        user_message,
                        portfolio_context=build_chat_context(user_id),
                        history=chat_history,
                    )
                except ChatServiceError as exc:
                    flash(str(exc), "danger")
                else:
                    chat_history = chat_history + [
                        {"role": "user", "content": user_message},
                        {"role": "assistant", "content": assistant_reply},
                    ]
                    session["chat_history"] = chat_history[-6:]
                    user_message = ""

        return render_template(
            "chat.html",
            chat_history=chat_history,
            user_message=user_message,
            assistant_reply=assistant_reply,
        )
