"""Portfolio management and holdings routes for the web application."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.routes.auth import get_authenticated_user_id
from app.routes.common import flash_message, parse_int, redirect_to, render_template
from app.services import portfolio_service as service


router = APIRouter()


@router.get("/dashboard")
def dashboard_page(request: Request):
    user_id = get_authenticated_user_id(request)
    return render_template(
        request,
        "dashboard.html",
        {
            "summary": service.calculate_portfolio_summary(user_id),
            "accounts": service.fetch_accounts(user_id),
            "holdings": service.calculate_holdings_by_symbol(user_id),
        },
    )


@router.get("/accounts")
async def accounts_page(request: Request):
    user_id = get_authenticated_user_id(request)
    editing_account = None
    edit_id = request.query_params.get("edit_id")
    if edit_id:
        edit_pk = parse_int(edit_id)
        if edit_pk is None:
            flash_message(request, "Account not found.", "danger")
            return redirect_to(request, "accounts_page")
        editing_account = service.fetch_account(edit_pk, user_id)
        if not editing_account:
            flash_message(request, "Account not found.", "danger")
            return redirect_to(request, "accounts_page")

    return render_template(
        request,
        "demat_accounts.html",
        {
            "accounts": service.fetch_accounts(user_id),
            "editing_account": editing_account,
        },
    )


@router.post("/accounts")
async def accounts_page_post(request: Request):
    user_id = get_authenticated_user_id(request)
    form = await request.form()
    broker_name = str(form.get("broker_name", "")).strip()
    account_id = str(form.get("account_id", "")).strip()
    if not broker_name:
        flash_message(request, "Broker name is required.", "danger")
        return redirect_to(request, "accounts_page")

    if account_id:
        account_pk = parse_int(account_id)
        if account_pk is None:
            flash_message(request, "Account not found.", "danger")
            return redirect_to(request, "accounts_page")
        ok, message = service.update_account(account_pk, user_id, broker_name)
        flash_message(request, message, "success" if ok else "danger")
        if ok:
            return redirect_to(request, "accounts_page")
    else:
        ok, message = service.create_account(user_id, broker_name)
        flash_message(request, message, "success" if ok else "danger")
        if ok:
            return redirect_to(request, "accounts_page")

    return redirect_to(request, "accounts_page")


@router.get("/accounts/delete/{account_id}")
def delete_account(request: Request, account_id: int):
    user_id = get_authenticated_user_id(request)
    ok, message = service.delete_account(account_id, user_id)
    flash_message(request, message, "success" if ok else "danger")
    return redirect_to(request, "accounts_page")


@router.get("/transactions")
async def transactions_page(request: Request):
    user_id = get_authenticated_user_id(request)
    editing_transaction = None
    edit_id = request.query_params.get("edit_id")
    if edit_id:
        edit_pk = parse_int(edit_id)
        if edit_pk is None:
            flash_message(request, "Transaction not found.", "danger")
            return redirect_to(request, "transactions_page")
        editing_transaction = service.fetch_transaction(edit_pk, user_id)
        if not editing_transaction:
            flash_message(request, "Transaction not found.", "danger")
            return redirect_to(request, "transactions_page")

    return render_template(
        request,
        "transactions.html",
        {
            "transactions": service.fetch_transactions(user_id),
            "accounts": service.fetch_accounts(user_id),
            "editing_transaction": editing_transaction,
        },
    )


@router.post("/transactions")
async def transactions_page_post(request: Request):
    user_id = get_authenticated_user_id(request)
    form = await request.form()
    transaction_id = str(form.get("transaction_id", "")).strip()
    account_id = str(form.get("account_id", "")).strip()
    stock_symbol = str(form.get("stock_symbol", "")).strip().upper()
    transaction_type = str(form.get("transaction_type", "")).strip().upper()
    quantity = str(form.get("quantity", "")).strip()
    price_per_share = str(form.get("price_per_share", "")).strip()
    transaction_date = str(form.get("transaction_date", "")).strip()

    account_pk = parse_int(account_id)
    tx_pk = parse_int(transaction_id) if transaction_id else None

    if account_pk is None or not stock_symbol or transaction_type not in {"BUY", "SELL"}:
        flash_message(request, "Please enter valid transaction details.", "danger")
        return redirect_to(request, "transactions_page")

    try:
        quantity_value = int(quantity)
        price_value = float(price_per_share)
    except ValueError:
        flash_message(request, "Quantity and price must be valid numbers.", "danger")
        return redirect_to(request, "transactions_page")

    if quantity_value <= 0:
        flash_message(request, "Quantity must be greater than zero.", "danger")
    elif price_value <= 0:
        flash_message(request, "Price per share must be greater than zero.", "danger")
    elif not transaction_date:
        flash_message(request, "Transaction date is required.", "danger")
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
        flash_message(request, message, "success" if ok else "danger")
        if ok:
            return redirect_to(request, "transactions_page")
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
        flash_message(request, message, "success" if ok else "danger")
        if ok:
            return redirect_to(request, "transactions_page")

    return redirect_to(request, "transactions_page")


@router.get("/transactions/delete/{transaction_id}")
def delete_transaction(request: Request, transaction_id: int):
    user_id = get_authenticated_user_id(request)
    ok, message = service.delete_transaction(transaction_id, user_id)
    flash_message(request, message, "success" if ok else "danger")
    return redirect_to(request, "transactions_page")


@router.api_route("/prices", methods=["GET", "POST"])
async def prices_page(request: Request):
    user_id = get_authenticated_user_id(request)
    holdings = service.calculate_holdings_by_symbol(user_id)
    holding_symbols = {item["stock_symbol"] for item in holdings}
    selected_symbol = ""
    entered_price = ""

    if request.method == "POST":
        form = await request.form()
        stock_symbol = str(form.get("stock_symbol", "")).strip().upper()
        current_price = str(form.get("current_price", "")).strip()
        selected_symbol = stock_symbol
        entered_price = current_price

        if not holdings:
            flash_message(request, "Add at least one stock transaction before updating prices.", "danger")
        elif not stock_symbol:
            flash_message(request, "Stock symbol is required.", "danger")
        elif stock_symbol not in holding_symbols:
            flash_message(request, "You can only update prices for stocks you currently hold.", "danger")
        else:
            try:
                current_price_value = float(current_price)
            except ValueError:
                flash_message(request, "Current price must be a valid number.", "danger")
            else:
                if current_price_value <= 0:
                    flash_message(request, "Current price must be greater than zero.", "danger")
                else:
                    ok, message = service.save_price(user_id, stock_symbol, current_price_value)
                    flash_message(request, message, "success" if ok else "danger")
                    if ok:
                        return redirect_to(request, "prices_page")

    return render_template(
        request,
        "stock_prices.html",
        {
            "holdings": holdings,
            "selected_symbol": selected_symbol,
            "entered_price": entered_price,
        },
    )


@router.get("/holdings")
def holdings_page(request: Request):
    user_id = get_authenticated_user_id(request)
    return render_template(
        request,
        "holdings.html",
        {"holdings": service.calculate_holdings_by_symbol(user_id)},
    )


@router.get("/account-summary")
def account_summary_page(request: Request):
    user_id = get_authenticated_user_id(request)
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

    return render_template(request, "account_summary.html", {"summaries": summaries})


@router.get("/portfolio-summary")
def portfolio_summary_page(request: Request):
    user_id = get_authenticated_user_id(request)
    return render_template(
        request,
        "portfolio_summary.html",
        {"summary": service.calculate_portfolio_summary(user_id)},
    )
